import argparse
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path


ROOT = Path(__file__).resolve().parent
URL = "http://127.0.0.1:8511"


def healthy():
    try:
        with urllib.request.urlopen(URL + "/api/health", timeout=1) as response:
            return response.status == 200 and json.load(response).get("app") == "traffic-lab-web"
    except (OSError, ValueError):
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    if sys.version_info[:2] != (3, 11):
        raise SystemExit("Use the isolated Python 3.11 environment: double-click Start.cmd.")
    if not healthy():
        with socket.socket() as sock:
            if sock.connect_ex(("127.0.0.1", 8511)) == 0:
                raise SystemExit("Port 8511 is occupied by another service. Close it before starting Traffic Lab.")
        (ROOT / "temp").mkdir(exist_ok=True)
        options = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {"start_new_session": True}
        with (ROOT / "temp" / "server.log").open("ab") as log:
            process = subprocess.Popen([sys.executable, str(ROOT / "web_server.py"), "--port", "8511"],
                                       cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, **options)
        (ROOT / "temp" / "server.json").write_text(json.dumps({"pid": process.pid, "url": URL}), encoding="utf-8")
        for _ in range(120):
            if healthy():
                break
            if process.poll() is not None:
                raise SystemExit("Server stopped during startup. See temp/server.log; rerun Setup.ps1 if dependencies are missing.")
            time.sleep(0.25)
        else:
            raise SystemExit("Server is taking longer than expected. Check temp/server.log and retry Start.cmd.")
    print("Traffic Lab is running at " + URL)
    if not args.no_browser:
        webbrowser.open(URL)


if __name__ == "__main__":
    main()
