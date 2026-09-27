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
