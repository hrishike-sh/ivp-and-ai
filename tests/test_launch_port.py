import errno
import json
import os
import socket
import subprocess
import sys
import textwrap
from pathlib import Path
from types import SimpleNamespace

import pytest

import launch


class MappedSocket:
    """Probe an owned ephemeral port without using the app's real port."""
    def __init__(self, address):
        self.inner = socket.socket()
        self.address = address

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.inner.close()

    def settimeout(self, timeout):
        self.inner.settimeout(timeout)

    def connect(self, address):
        self.inner.connect(self.address)

    def connect_ex(self, address):
        return self.inner.connect_ex(self.address)


@pytest.mark.parametrize("error", [TimeoutError("Probe timed out"), OSError(errno.EHOSTUNREACH, "Probe unreachable")],
                         ids=["timeout", "unreachable"])
def test_unverified_port_does_not_start_a_server(tmp_path, monkeypatch, error):
    class ErrorPort:
        timeout = None
        closed = False

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.closed = True

        def settimeout(self, timeout):
            self.timeout = timeout

        def connect(self, address):
            raise error

        def connect_ex(self, address):
            return error.errno or errno.ETIMEDOUT

    def unexpected_start(*args, **kwargs):
        pytest.fail("An unverified port must not start a competing server")

    probe = ErrorPort()
    monkeypatch.setattr(launch, "ROOT", tmp_path)
    monkeypatch.setattr(launch, "healthy", lambda: False)
    monkeypatch.setattr(launch, "socket", SimpleNamespace(socket=lambda: probe))
    monkeypatch.setattr(launch.subprocess, "Popen", unexpected_start)
    with pytest.raises(SystemExit, match="Could not check port 8511"):
        launch._ensure_server()
    assert probe.timeout is not None and probe.timeout > 0
    assert probe.closed
    assert not list(tmp_path.iterdir())


def test_refused_loopback_port_allows_server_startup(tmp_path, monkeypatch):
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        address = listener.getsockname()
    started = []

    def start_server(*args, **kwargs):
        started.append(1)
        return SimpleNamespace(pid=4000, poll=lambda: None)

    monkeypatch.setattr(launch, "ROOT", tmp_path)
    monkeypatch.setattr(launch, "healthy", lambda: bool(started))
    monkeypatch.setattr(launch, "socket", SimpleNamespace(socket=lambda: MappedSocket(address)))
    monkeypatch.setattr(launch.subprocess, "Popen", start_server)
    launch._ensure_server()
    assert started == [1]
    assert json.loads((tmp_path / "temp" / "server.json").read_text())["pid"] == 4000


@pytest.mark.skipif(os.name == "nt", reason="This case exercises POSIX loopback listen-queue saturation.")
def test_saturated_loopback_port_does_not_hang_the_launcher(tmp_path):
    listener = socket.socket()
    clients = []
    process = None
    try:
        listener.bind(("127.0.0.1", 0))
        listener.listen(0)
        address = listener.getsockname()
        for _ in range(8):
            client = socket.socket()
            client.settimeout(.1)
            try:
                client.connect(address)
            except TimeoutError:
                client.close()
                break
            except BaseException:
                client.close()
                raise
            clients.append(client)
        else:
            pytest.fail("Could not saturate the owned listener")
        code = textwrap.dedent("""
            import sys
            from pathlib import Path
            from types import SimpleNamespace
            import launch
            from tests.test_launch_port import MappedSocket
            address = ('127.0.0.1', int(sys.argv[1]))
            launch.ROOT = Path(sys.argv[2])
            launch.healthy = lambda: False
            launch.socket = SimpleNamespace(socket=lambda: MappedSocket(address))
            def unexpected_start(*args, **kwargs):
                raise AssertionError('An unverified port must not start a server')
            launch.subprocess.Popen = unexpected_start
            try:
                launch._ensure_server()
            except SystemExit as exc:
                print(exc, flush=True)
            else:
                raise AssertionError('The saturated port must stop startup')
        """)
        process = subprocess.Popen([sys.executable, "-c", code, str(address[1]), str(tmp_path)],
                                   cwd=Path(launch.__file__).resolve().parent,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        # The watchdog also bounds the pre-fix blocking probe; cleanup owns this child.
        output, errors = process.communicate(timeout=3)
        assert process.returncode == 0, errors
        assert "Could not check port 8511" in output
        assert not list(tmp_path.iterdir())
    finally:
        if process is not None:
            if process.poll() is None:
                process.kill()
            process.communicate(timeout=5)
        for client in clients:
            client.close()
        listener.close()
