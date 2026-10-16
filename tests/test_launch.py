import errno
import json
import os
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import pytest

import launch


class AvailablePort:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def connect_ex(self, address):
        return 1


@pytest.fixture
def launcher(tmp_path, monkeypatch):
    monkeypatch.setattr(launch, "ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["launch.py", "--no-browser"])
    monkeypatch.setattr(launch, "socket", SimpleNamespace(socket=AvailablePort))
    return tmp_path


def test_concurrent_launchers_start_one_server_and_preserve_its_pid(launcher, monkeypatch):
    ready = threading.Event()
    first_started = threading.Event()
    second_spawned = threading.Event()
    calls = []
    calls_lock = threading.Lock()

    def start_server(*args, **kwargs):
        with calls_lock:
            pid = 4000 + len(calls)
            calls.append(pid)
        if pid == 4000:
            first_started.set()
            # Keep startup in progress while the second launcher enters main.
            second_spawned.wait(timeout=2)
        else:
            second_spawned.set()
        ready.set()
        return SimpleNamespace(pid=pid, poll=lambda: None)

    monkeypatch.setattr(launch, "healthy", ready.is_set)
    monkeypatch.setattr(subprocess, "Popen", start_server)
    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(launch.main)
        assert first_started.wait(timeout=3)
        second = executor.submit(launch.main)
        first.result(timeout=6)
        second.result(timeout=6)
    assert calls == [4000]
    saved = json.loads((launcher / "temp" / "server.json").read_text(encoding="utf-8"))
    assert saved["pid"] == 4000


def test_healthy_server_during_startup_still_waits_for_pid_publication(launcher, monkeypatch):
    ready = threading.Event()
    writing_pid = threading.Event()
    release_write = threading.Event()
    original_write = Path.write_text
    saved = launcher / "temp" / "server.json"

    def start_server(*args, **kwargs):
        ready.set()
        return SimpleNamespace(pid=4000, poll=lambda: None)

    def delayed_pid_write(path, *args, **kwargs):
        if path == saved:
            writing_pid.set()
            assert release_write.wait(timeout=3)
        return original_write(path, *args, **kwargs)

    monkeypatch.setattr(launch, "healthy", ready.is_set)
    monkeypatch.setattr(subprocess, "Popen", start_server)
    monkeypatch.setattr(Path, "write_text", delayed_pid_write)
    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(launch.main)
        try:
            assert writing_pid.wait(timeout=3)
            second = executor.submit(launch.main)
            with pytest.raises(TimeoutError):
                second.result(timeout=.2)
        finally:
            release_write.set()
        first.result(timeout=5)
        second.result(timeout=5)
    assert json.loads(saved.read_text(encoding="utf-8"))["pid"] == 4000


def test_startup_failure_allows_a_later_launcher_to_retry(launcher, monkeypatch):
    ready = threading.Event()
    attempts = []

    def start_server(*args, **kwargs):
        attempts.append(1)
        if len(attempts) == 1:
            raise OSError("Deliberate startup failure")
        ready.set()
        return SimpleNamespace(pid=4001, poll=lambda: None)

    monkeypatch.setattr(launch, "healthy", ready.is_set)
    monkeypatch.setattr(subprocess, "Popen", start_server)
    with pytest.raises(OSError, match="Deliberate startup failure"):
        launch.main()
    launch.main()
    assert len(attempts) == 2
    saved = json.loads((launcher / "temp" / "server.json").read_text(encoding="utf-8"))
    assert saved["pid"] == 4001


def test_healthy_server_is_reused_without_overwriting_its_pid(launcher, monkeypatch):
    folder = launcher / "temp"
    folder.mkdir()
    saved = folder / "server.json"
    original = b'{"pid": 4000, "url": "http://127.0.0.1:8511"}'
    saved.write_bytes(original)
    monkeypatch.setattr(launch, "healthy", lambda: True)

    def unexpected_start(*args, **kwargs):
        pytest.fail("An existing healthy server should be reused")

    monkeypatch.setattr(subprocess, "Popen", unexpected_start)
    launch.main()
    assert saved.read_bytes() == original


def test_busy_startup_lock_times_out_and_releases_afterward(launcher):
    with launch.startup_lock():
        with pytest.raises(SystemExit, match="Another Traffic Lab launcher"):
            with launch.startup_lock(timeout=0):
                pytest.fail("The second launcher must not enter while startup is locked")
    with launch.startup_lock(timeout=0):
        pass


def test_startup_lock_excludes_another_process(launcher):
    code = ("import launch,sys; from pathlib import Path; launch.ROOT=Path(sys.argv[1]);\n"
            "with launch.startup_lock():\n print('ready',flush=True)\n sys.stdin.readline()")
    process = subprocess.Popen([sys.executable, "-c", code, str(launcher)],
                               cwd=Path(launch.__file__).resolve().parent,
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    try:
        assert process.stdout.readline().strip() == "ready"
        with pytest.raises(SystemExit, match="Another Traffic Lab launcher"):
            with launch.startup_lock(timeout=0):
                pytest.fail("A second process must not enter startup")
    finally:
        process.communicate("\n", timeout=5)
    assert process.returncode == 0


@pytest.mark.parametrize("fail_inside", [False, True])
def test_windows_startup_lock_retries_and_unlocks_the_same_byte(launcher, monkeypatch, fail_inside):
    calls = []
    sleeps = []

    def locking(fd, mode, count):
        calls.append((mode, count, os.lseek(fd, 0, os.SEEK_CUR)))
        if len(calls) == 1:
            raise OSError(errno.EACCES, "Startup is locked")

    monkeypatch.setattr(launch, "os", SimpleNamespace(name="nt"))
    monkeypatch.setitem(sys.modules, "msvcrt", SimpleNamespace(locking=locking, LK_NBLCK=1, LK_UNLCK=2))
    monkeypatch.setattr(launch, "time", SimpleNamespace(monotonic=lambda: 0., sleep=sleeps.append))
    if fail_inside:
        with pytest.raises(RuntimeError, match="Startup failed"):
            with launch.startup_lock():
                raise RuntimeError("Startup failed")
    else:
        with launch.startup_lock():
            pass
    assert calls == [(1, 1, 0), (1, 1, 0), (2, 1, 0)]
    assert sleeps == [.1]


@pytest.mark.skipif(os.name == "nt", reason="This case exercises POSIX flock errors.")
def test_startup_lock_does_not_hide_unexpected_locking_errors(launcher, monkeypatch):
    import fcntl

    def fail_lock(*args):
        raise OSError(errno.EBADF, "Invalid lock handle")

    monkeypatch.setattr(fcntl, "flock", fail_lock)
    with pytest.raises(OSError, match="Invalid lock handle"):
        with launch.startup_lock():
            pytest.fail("A failed lock must not enter startup")
