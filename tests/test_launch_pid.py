import contextlib
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import pytest

import launch
from tests.test_launch import StartingServer, launcher as launcher


@pytest.fixture
def starting_server(launcher, monkeypatch):
    process = StartingServer()
    started = []

    def start(*args, **kwargs):
        started.append(1)
        return process

    monkeypatch.setattr(launch, "healthy", lambda: bool(started))
    monkeypatch.setattr(launch.subprocess, "Popen", start)
    return process


@pytest.mark.parametrize("previous_record", [False, True], ids=["first-start", "replace-record"])
def test_pid_record_is_not_visible_until_write_completes(launcher, starting_server, monkeypatch, previous_record):
    folder = launcher / "temp"
    folder.mkdir()
    saved = folder / "server.json"
    original = b'{"pid": 3500, "url": "http://127.0.0.1:8511"}'
    if previous_record:
        saved.write_bytes(original)
    original_open = Path.open
    writing = threading.Event()
    release = threading.Event()

    @contextlib.contextmanager
    def paused_file(file):
        with file:
            writing.set()
            assert release.wait(timeout=5)
            yield file

    def pause_open(path, mode="r", *args, **kwargs):
        file = original_open(path, mode, *args, **kwargs)
        if path.name == saved.name and path.is_relative_to(folder) and mode == "w":
            return paused_file(file)
        return file

    monkeypatch.setattr(Path, "open", pause_open)
    with ThreadPoolExecutor(max_workers=1) as executor:
        startup = executor.submit(launch.main)
        try:
            assert writing.wait(timeout=5)
            if previous_record:
                assert saved.read_bytes() == original
            else:
                assert not saved.exists()
        finally:
            release.set()
        startup.result(timeout=5)
    assert json.loads(saved.read_text())["pid"] == starting_server.pid
    assert all(path.is_file() for path in folder.iterdir())


def test_pid_replacement_failure_preserves_previous_record_and_stops_child(launcher, starting_server, monkeypatch):
    folder = launcher / "temp"
    folder.mkdir()
    saved = folder / "server.json"
    original = b'{"pid": 3500, "url": "http://127.0.0.1:8511"}'
    saved.write_bytes(original)
    original_replace = Path.replace
    attempts = []
    sleeps = []

    def deny_publish(path, destination):
        if Path(destination) == saved:
            attempts.append(path)
            if len(attempts) > 8:
                pytest.fail("PID publication retries must be bounded")
            raise PermissionError("Cannot replace server PID")
        return original_replace(path, destination)

    monkeypatch.setattr(Path, "replace", deny_publish)
    monkeypatch.setattr(launch, "time", SimpleNamespace(monotonic=launch.time.monotonic, sleep=sleeps.append))
    with pytest.raises(PermissionError, match="Cannot replace server PID"):
        launch.main()
    assert starting_server.poll() is not None
    assert saved.read_bytes() == original
    assert attempts
    assert all(path.is_file() for path in folder.iterdir())


def test_transient_pid_replacement_denial_recovers(launcher, starting_server, monkeypatch):
    saved = launcher / "temp" / "server.json"
    original_replace = Path.replace
    attempts = []
    sleeps = []

    def temporarily_locked(path, destination):
        if Path(destination) == saved:
            attempts.append(path)
            if len(attempts) < 3:
                raise PermissionError("PID reader still has the file open")
        return original_replace(path, destination)

    monkeypatch.setattr(Path, "replace", temporarily_locked)
    monkeypatch.setattr(launch, "time", SimpleNamespace(monotonic=launch.time.monotonic, sleep=sleeps.append))
    launch.main()
    assert len(attempts) == 3
    assert sleeps == [.02, .04]
    assert json.loads(saved.read_text())["pid"] == starting_server.pid
    assert starting_server.poll() is None
    assert all(path.is_file() for path in saved.parent.iterdir())
