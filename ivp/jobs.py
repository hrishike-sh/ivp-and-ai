import contextlib
import json
import os
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .media import hidden_process_options, write_json


ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "runs"


def now():
    return datetime.now(timezone.utc).isoformat()


@contextlib.contextmanager
def job_lock():
    RUNS.mkdir(exist_ok=True)
    with (RUNS / ".worker.lock").open("a+b") as lock:
        lock.seek(0)
        if os.name == "nt":
            import msvcrt
            if (RUNS / ".worker.lock").stat().st_size == 0:
                lock.write(b"0")
                lock.flush()
                lock.seek(0)
            try:
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise RuntimeError("Another video job is running. Cancel it or wait for it to finish.") from exc
            try:
                yield
            finally:
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise RuntimeError("Another video job is running.") from exc
            try:
                yield
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)


def new_run():
    path = RUNS / (datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8])
    path.mkdir(parents=True)
    return path


def read_status(run):
    try:
        return json.loads((Path(run) / "status.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"state": "unknown", "message": "Waiting for job status."}


def refreshed_status(run):
    state = read_status(run)
    if state.get("state") not in ("queued", "running", "encoding"):
        return state
    age = (datetime.now(timezone.utc) - datetime.fromisoformat(state["updated_at"])).total_seconds()
    if age < 30:
        return state
    try:
        with job_lock():
            state = {**state, "state": "interrupted", "message": "Worker stopped unexpectedly. Start a new run from the original upload.", "updated_at": now()}
            write_json(Path(run) / "status.json", state)
    except RuntimeError:
        pass
    return state


def start_video(path, info, settings, selected_masks, ai=False):
    executable, module = sys.executable, "ivp.worker"
    if ai:
        from traffic_ai.runtime import python_path

        executable, module = str(python_path()), "traffic_ai.worker"
        if not Path(executable).is_file():
            raise RuntimeError("AI runtime is missing. Run Setup-AI.ps1 in the project folder first.")
    with job_lock():
        recent = sorted(RUNS.glob("*/status.json"), reverse=True)
        for status_path in recent:
            state = read_status(status_path.parent)
            if state.get("state") in ("queued", "running", "encoding"):
                age = (datetime.now(timezone.utc) - datetime.fromisoformat(state["updated_at"])).total_seconds()
                if age < 30:
                    raise RuntimeError("A video job is starting or running. Wait for it to finish or cancel it.")
                write_json(status_path, {**state, "state": "interrupted", "message": "Previous worker stopped unexpectedly.", "updated_at": now()})
        run = new_run()
        write_json(run / "request.json", {"source": str(Path(path).resolve()), "info": info,
                   "settings": settings.to_dict(), "selected_masks": selected_masks, "created_at": now(), "ai": ai})
        write_json(run / "status.json", {"state": "queued", "progress": 0, "updated_at": now(), "message": "Starting video worker."})
        with (run / "worker.log").open("wb") as log:
            process = subprocess.Popen([executable, "-m", module, str(run)], cwd=ROOT,
                                       stdout=log, stderr=subprocess.STDOUT, **hidden_process_options())
        write_json(run / "process.json", {"pid": process.pid})
        return run


def cancel_job(run):
    (Path(run) / "cancel.request").touch()


def history():
    return sorted(RUNS.glob("*/status.json"), reverse=True)[:30] if RUNS.exists() else []
