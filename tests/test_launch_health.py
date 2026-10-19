import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace

import pytest

import launch


@pytest.fixture
def health_server(monkeypatch):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.server.requests.append(self.path)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(self.server.body)))
            self.end_headers()
            self.wfile.write(self.server.body)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.body = b"null"
    server.requests = []
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": .01}, daemon=True)
    thread.start()
    monkeypatch.setattr(launch, "URL", f"http://127.0.0.1:{server.server_port}")
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
        assert not thread.is_alive()


@pytest.mark.parametrize("payload", [None, [], "ok", True, 42],
                         ids=["null", "array", "string", "boolean", "number"])
def test_nonobject_health_response_is_unhealthy(health_server, payload):
    health_server.body = json.dumps(payload).encode()
    assert launch.healthy() is False
    assert health_server.requests == ["/api/health"]


@pytest.mark.parametrize("payload,expected", [
    ({"app": "traffic-lab-web", "version": 2}, True),
    ({"app": "another-service"}, False),
    ({}, False),
])
def test_health_check_requires_the_traffic_lab_marker(health_server, payload, expected):
    health_server.body = json.dumps(payload).encode()
    assert launch.healthy() is expected
    assert health_server.requests == ["/api/health"]


def test_nonobject_health_response_preserves_the_port_conflict_diagnostic(health_server, tmp_path, monkeypatch):
    class OccupiedPort:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def connect_ex(self, address):
            assert address == ("127.0.0.1", 8511)
            return 0

    def unexpected_start(*args, **kwargs):
        pytest.fail("An occupied port must not start a competing server")

    monkeypatch.setattr(launch, "ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["launch.py", "--no-browser"])
    monkeypatch.setattr(launch, "socket", SimpleNamespace(socket=OccupiedPort))
    monkeypatch.setattr(launch.subprocess, "Popen", unexpected_start)
    saved = tmp_path / "temp" / "server.json"
    saved.parent.mkdir()
    original = b'{"pid": 54321, "url": "http://127.0.0.1:8511"}'
    saved.write_bytes(original)
    health_server.body = b"[]"
    with pytest.raises(SystemExit, match="Port 8511 is occupied by another service"):
        launch.main()
    assert saved.read_bytes() == original
    assert health_server.requests == ["/api/health"]
