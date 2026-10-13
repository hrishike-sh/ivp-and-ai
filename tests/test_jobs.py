import contextlib
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

import pytest

import ivp.jobs as jobs
from ivp.media import hidden_process_options, write_json


def test_exclusive_lock_rejects_second_worker(tmp_path, monkeypatch):
    monkeypatch.setattr(jobs, "RUNS", tmp_path)
    code = "import ivp.jobs as jobs; import sys,time; from pathlib import Path; jobs.RUNS=Path(sys.argv[1]);\nwith jobs.job_lock():\n print('ready',flush=True)\n time.sleep(15)"
    process = subprocess.Popen([sys.executable, "-c", code, str(tmp_path)], cwd=jobs.ROOT, stdout=subprocess.PIPE, text=True, **hidden_process_options())
    try:
        assert process.stdout.readline().strip() == "ready"
        with pytest.raises(RuntimeError, match="Another video job"):
            with jobs.job_lock():
                pass
    finally:
        process.terminate()
        process.wait(timeout=5)


def test_interrupted_job_recovery(tmp_path, monkeypatch):
    monkeypatch.setattr(jobs, "RUNS", tmp_path)
    run = tmp_path / "old"
    run.mkdir()
    old = (datetime.now(timezone.utc) - timedelta(minutes=3)).isoformat()
    write_json(run / "status.json", {"state": "running", "updated_at": old})
    assert jobs.refreshed_status(run)["state"] == "interrupted"


@pytest.mark.parametrize("latest_state", ["complete", "cancelled", "failed", "queued", "running", "encoding"])
def test_recovery_rechecks_status_after_acquiring_lock(tmp_path, monkeypatch, latest_state):
    monkeypatch.setattr(jobs, "RUNS", tmp_path)
    run = tmp_path / "changing"
    run.mkdir()
    old = (datetime.now(timezone.utc) - timedelta(minutes=3)).isoformat()
    write_json(run / "status.json", {"state": "running", "updated_at": old})
    latest = {"state": latest_state, "message": "Latest worker status", "progress": .9,
              "updated_at": jobs.now() if latest_state in ("queued", "running", "encoding") else old}
    original_lock = jobs.job_lock

    @contextlib.contextmanager
    def worker_updates_before_lock():
        # The refresh has read the old status; the worker updates before it can lock.
        write_json(run / "status.json", latest)
        with original_lock():
            yield

    monkeypatch.setattr(jobs, "job_lock", worker_updates_before_lock)
    assert jobs.refreshed_status(run) == latest
    assert jobs.read_status(run) == latest


def test_stale_status_is_preserved_while_worker_holds_lock(tmp_path, monkeypatch):
    monkeypatch.setattr(jobs, "RUNS", tmp_path)
    run = tmp_path / "active"
    run.mkdir()
    old = (datetime.now(timezone.utc) - timedelta(minutes=3)).isoformat()
    status = {"state": "running", "updated_at": old, "message": "Long inference"}
    write_json(run / "status.json", status)
    with jobs.job_lock():
        assert jobs.refreshed_status(run) == status
    assert jobs.read_status(run) == status
