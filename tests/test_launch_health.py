import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace

import pytest

import launch


BROKEN_HTTP_RESPONSES = [
    pytest.param(b'HTTP/1.1 200 OK\r\nContent-Length: 50\r\nConnection: close\r\n\r\n{"app":"traffic-lab-web"}',
                 id="truncated-content-length"),
    pytest.param(b'HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\nConnection: close\r\n\r\n19\r\n{"app":"traffic-lab-web"}\r\n',
                 id="missing-final-chunk"),
    pytest.param(b'not an HTTP status\r\n\r\n', id="invalid-status-line"),
    pytest.param(b'HTTP/1.1 200 OK\r\nX-Test: ' + b'x' * 65536 + b'\r\n\r\n',
                 id="oversized-header"),
]


@pytest.fixture
def health_server(monkeypatch):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.server.requests.append(self.path)
            if self.server.raw_responses:
                self.wfile.write(self.server.raw_responses.pop(0))
                self.close_connection = True
                return
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
    server.raw_responses = []
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


@pytest.mark.parametrize("raw_response", BROKEN_HTTP_RESPONSES)
def test_broken_http_health_response_is_unhealthy(health_server, raw_response):
    health_server.raw_responses = [raw_response]
    assert launch.healthy() is False
    assert health_server.requests == ["/api/health"]


@pytest.mark.parametrize("raw_response", [pytest.param(None, id="nonobject-json"), *BROKEN_HTTP_RESPONSES])
def test_unhealthy_response_preserves_the_port_conflict_diagnostic(health_server, tmp_path, monkeypatch, raw_response):
    class OccupiedPort:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def settimeout(self, timeout):
            pass

        def connect(self, address):
            assert address == ("127.0.0.1", 8511)

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
    if raw_response is not None:
        health_server.raw_responses = [raw_response]
    with pytest.raises(SystemExit, match="Port 8511 is occupied by another service"):
        launch.main()
    assert saved.read_bytes() == original
    assert health_server.requests == ["/api/health"]


def test_startup_retries_after_a_broken_http_health_response(health_server, tmp_path, monkeypatch):
    class AvailablePort:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def settimeout(self, timeout):
            pass

        def connect(self, address):
            raise ConnectionRefusedError("Port is unused")

    started = []
    stopped = []
    process = SimpleNamespace(pid=4000, poll=lambda: 0 if stopped else None,
                              terminate=lambda: stopped.append(True), wait=lambda timeout: 0)

    def start_server(*args, **kwargs):
        started.append(process)
        return process

    monkeypatch.setattr(launch, "ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["launch.py", "--no-browser"])
    monkeypatch.setattr(launch, "socket", SimpleNamespace(socket=AvailablePort))
    monkeypatch.setattr(launch.subprocess, "Popen", start_server)
    broken = b'HTTP/1.1 200 OK\r\nContent-Length: 50\r\n\r\n{"app":"traffic-lab-web"}'
    health_server.raw_responses = [b'HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\n{}', broken]
    health_server.body = b'{"app":"traffic-lab-web"}'

    launch.main()

    assert started == [process]
    assert stopped == []
    assert health_server.requests == ["/api/health"] * 3
    saved = json.loads((tmp_path / "temp" / "server.json").read_text(encoding="utf-8"))
    assert saved == {"pid": process.pid, "url": launch.URL}
