from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Dict
import threading
import time
import uuid
import subprocess

from core.security import validate_admin_secret

router = APIRouter(prefix="/api", tags=["admin-retrain"])

RETRAIN_JOBS: dict[str, dict] = {}
SCHEDULER_THREAD: threading.Thread | None = None
SCHEDULER_EVENT = threading.Event()
SCHEDULER_CONFIG = {"enabled": False, "interval_minutes": 1440, "last_run": None}


def _run_auto_retrain(job_id: str, params: dict):
    RETRAIN_JOBS[job_id] = {"status": "running", "started_at": time.time(), "output": None}
    try:
        cmd = ["python", "scripts/auto_retrain.py"]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        out_lines = []
        for line in proc.stdout:
            out_lines.append(line)
        proc.wait()
        RETRAIN_JOBS[job_id]["status"] = "finished" if proc.returncode == 0 else "failed"
        RETRAIN_JOBS[job_id]["finished_at"] = time.time()
        RETRAIN_JOBS[job_id]["returncode"] = proc.returncode
        RETRAIN_JOBS[job_id]["output"] = "".join(out_lines[-200:])
    except Exception as exc:
        RETRAIN_JOBS[job_id]["status"] = "failed"
        RETRAIN_JOBS[job_id]["finished_at"] = time.time()
        RETRAIN_JOBS[job_id]["output"] = str(exc)


def _scheduler_loop(interval_minutes: int):
    SCHEDULER_EVENT.clear()
    while not SCHEDULER_EVENT.wait(interval_minutes * 60):
        job_id = str(uuid.uuid4())
        RETRAIN_JOBS[job_id] = {"status": "queued", "started_at": time.time()}
        t = threading.Thread(target=_run_auto_retrain, args=(job_id, {}), daemon=True)
        t.start()
        SCHEDULER_CONFIG["last_run"] = time.time()


def start_auto_retrain_scheduler(interval_minutes: int = 1440) -> bool:
    global SCHEDULER_THREAD
    if SCHEDULER_THREAD and SCHEDULER_THREAD.is_alive():
        return False
    SCHEDULER_EVENT.clear()
    SCHEDULER_CONFIG.update({"enabled": True, "interval_minutes": interval_minutes})
    SCHEDULER_THREAD = threading.Thread(target=_scheduler_loop, args=(interval_minutes,), daemon=True)
    SCHEDULER_THREAD.start()
    return True


def stop_auto_retrain_scheduler() -> bool:
    global SCHEDULER_THREAD
    if not SCHEDULER_THREAD:
        SCHEDULER_CONFIG.update({"enabled": False})
        return False
    SCHEDULER_EVENT.set()
    SCHEDULER_THREAD = None
    SCHEDULER_CONFIG.update({"enabled": False})
    return True


@router.post('/admin/auto-retrain/schedule')
def schedule_auto_retrain(payload: Dict = {}, request: Request = None):
    validate_admin_secret(request)
    try:
        interval = int(payload.get("interval_minutes", 1440))
    except Exception:
        raise HTTPException(status_code=400, detail="Paramètre interval_minutes invalide")
    started = start_auto_retrain_scheduler(interval)
    return {"status": "scheduled" if started else "already_running", "interval_minutes": interval}


@router.delete('/admin/auto-retrain/schedule')
def unschedule_auto_retrain(request: Request):
    validate_admin_secret(request)
    stopped = stop_auto_retrain_scheduler()
    return {"status": "stopped" if stopped else "not_running"}


@router.get('/admin/auto-retrain/schedule')
def get_schedule_status(request: Request):
    validate_admin_secret(request)
    return SCHEDULER_CONFIG


@router.post('/admin/auto-retrain')
def admin_auto_retrain(payload: Dict = {}, request: Request = None):
    validate_admin_secret(request)
    job_id = str(uuid.uuid4())
    RETRAIN_JOBS[job_id] = {"status": "queued", "started_at": time.time()}
    t = threading.Thread(target=_run_auto_retrain, args=(job_id, payload), daemon=True)
    t.start()
    return {"job_id": job_id, "status": "queued"}


@router.get('/admin/auto-retrain/{job_id}')
def admin_auto_retrain_status(job_id: str, request: Request):
    validate_admin_secret(request)
    job = RETRAIN_JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
