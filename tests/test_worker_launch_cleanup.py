import contextlib
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

import ivp.jobs as jobs
from ivp.pipeline import Settings


@pytest.fixture
def worker_launch(tmp_path, monkeypatch):
    monkeypatch.setattr(jobs, "RUNS", tmp_path / "runs")
    source = tmp_path / "original.mp4"
    source.write_bytes(b"original upload")
    state = SimpleNamespace(source=source, children=[], commands=[], waits=[], terminated=[], stubborn=False)
    original_popen = subprocess.Popen
    original_waits = {}

    def start(command, **kwargs):
        state.commands.append(command)
        ready = Path(command[-1]) / "child.ready"
        code = """
import signal, sys
from pathlib import Path
if sys.argv[2] == 'stubborn':
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
print('Waiting for launch metadata', flush=True)
Path(sys.argv[1]).touch()
sys.stdin.read()
"""
        child = original_popen([sys.executable, "-c", code, str(ready),
                                "stubborn" if state.stubborn else "cooperative"],
                               stdin=subprocess.PIPE, **kwargs)
        state.children.append(child)
        original_wait = child.wait
        original_waits[child.pid] = original_wait
        original_terminate = child.terminate

        def terminate():
            # Cleanup must finish while the launcher still owns the worker lock.
            with pytest.raises(RuntimeError, match="Another video job"):
                with jobs.job_lock():
                    pass
            state.terminated.append(child.pid)
            original_terminate()

        def wait(timeout=None):
            state.waits.append(timeout)
            # Exercise actual SIGTERM resistance without waiting five seconds.
            return original_wait(timeout=.1 if state.stubborn and len(state.waits) == 1 else timeout)

        child.terminate = terminate
        child.wait = wait
        deadline = time.monotonic() + 5
        while not ready.exists():
            assert child.poll() is None
            assert time.monotonic() < deadline, "Test child did not become ready"
            time.sleep(.01)
        return child

    monkeypatch.setattr(jobs.subprocess, "Popen", start)
    try:
        yield state
    finally:
        for child in state.children:
            if child.poll() is None:
                child.kill()
            original_waits[child.pid](timeout=5)
            child.stdin.close()


def fail_pid_publication(monkeypatch, error):
    original_write = jobs.write_json

    def write(path, payload):
        if path.name == "process.json":
            raise error
        return original_write(path, payload)

    monkeypatch.setattr(jobs, "write_json", write)
    return original_write


@pytest.mark.parametrize("mode,module", [
    ("ivp", "ivp.worker"), ("motion", "ivp.motion_worker"),
])
def test_pid_publication_failure_reaps_worker_and_allows_immediate_retry(worker_launch, monkeypatch, mode, module):
    options = {"motion": {"tracking_mode": "ivp"}} if mode == "motion" else {}
    original_new_run = jobs.new_run

    def blocked_pid_path():
        run = original_new_run()
        (run / "process.json").mkdir()
        return run

    monkeypatch.setattr(jobs, "new_run", blocked_pid_path)

    with pytest.raises(RuntimeError, match="Could not start the processing worker") as error:
        jobs.start_video(worker_launch.source, {"kind": "video"}, Settings(), [], **options)

    child, = worker_launch.children
    assert child.poll() is not None
    assert worker_launch.terminated == [child.pid]
    assert worker_launch.waits == [5]
    assert worker_launch.commands[0][1:3] == ["-m", module]
    run = next(jobs.RUNS.glob("*/status.json")).parent
    status = jobs.read_status(run)
    assert status["state"] == "failed" and status["progress"] == 0
    assert isinstance(error.value.__cause__, OSError)
    assert str(error.value.__cause__) in status["message"]
    request = json.loads((run / "request.json").read_text())
    assert request["source"] == str(worker_launch.source.resolve())
    assert "ai" not in request
    assert request["motion"] == options.get("motion")
    assert (run / "worker.log").read_text().strip() == "Waiting for launch metadata"
    assert (run / "process.json").is_dir()
    assert not list(run.glob("*.tmp"))
    assert worker_launch.source.read_bytes() == b"original upload"
    with jobs.job_lock():
        pass

    monkeypatch.setattr(jobs, "new_run", original_new_run)
    monkeypatch.setattr(jobs.subprocess, "Popen", lambda *args, **kwargs: SimpleNamespace(pid=123))
    retry = jobs.start_video(worker_launch.source, {"kind": "video"}, Settings(), [], **options)
    assert retry != run
    assert jobs.read_status(retry)["state"] == "queued"
    assert json.loads((retry / "process.json").read_text()) == {"pid": 123}
    assert jobs.read_status(run) == status


def test_interruption_after_spawn_reaps_worker_and_preserves_interruption(worker_launch, monkeypatch):
    fail_pid_publication(monkeypatch, KeyboardInterrupt("Stop launch"))
    with pytest.raises(KeyboardInterrupt, match="Stop launch"):
        jobs.start_video(worker_launch.source, {"kind": "video"}, Settings(), [])
    child, = worker_launch.children
    assert child.poll() is not None
    assert worker_launch.terminated == [child.pid]
    run = next(jobs.RUNS.glob("*/status.json")).parent
    assert jobs.read_status(run)["state"] == "failed"
    assert (run / "request.json").is_file()
    assert worker_launch.source.read_bytes() == b"original upload"


def test_log_close_failure_reaps_the_started_worker(worker_launch, monkeypatch):
    original_open = Path.open

    @contextlib.contextmanager
    def failing_close(file):
        with file:
            yield file
        raise OSError("Worker log close failed")

    def open_file(path, *args, **kwargs):
        file = original_open(path, *args, **kwargs)
        return failing_close(file) if path.name == "worker.log" else file

    monkeypatch.setattr(Path, "open", open_file)
    with pytest.raises(RuntimeError, match="Worker log close failed"):
        jobs.start_video(worker_launch.source, {"kind": "video"}, Settings(), [])
    child, = worker_launch.children
    assert child.poll() is not None
    run = next(jobs.RUNS.glob("*/status.json")).parent
    assert jobs.read_status(run)["state"] == "failed"


@pytest.mark.skipif(os.name == "nt", reason="POSIX signal resistance; Windows uses TerminateProcess.")
def test_stubborn_worker_is_killed_and_reaped_before_launch_returns(worker_launch, monkeypatch):
    worker_launch.stubborn = True
    fail_pid_publication(monkeypatch, PermissionError("Cannot publish worker PID"))
    with pytest.raises(RuntimeError, match="Cannot publish worker PID"):
        jobs.start_video(worker_launch.source, {"kind": "video"}, Settings(), [])
    child, = worker_launch.children
    assert child.returncode == -signal.SIGKILL
    assert worker_launch.waits == [5, 5]
    run = next(jobs.RUNS.glob("*/status.json")).parent
    assert jobs.read_status(run)["state"] == "failed"


def test_successful_launch_keeps_its_worker_and_publishes_the_pid(worker_launch):
    run = jobs.start_video(worker_launch.source, {"kind": "video"}, Settings(), [])
    child, = worker_launch.children
    assert child.poll() is None
    assert worker_launch.terminated == [] and worker_launch.waits == []
    assert jobs.read_status(run)["state"] == "queued"
    assert json.loads((run / "process.json").read_text()) == {"pid": child.pid}
