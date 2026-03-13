import os
import threading
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler

from app.core.database import SessionLocal
from app.core.scanner import run_full_scan


class ScanState:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.running = False
        self.last_started: datetime | None = None
        self.last_completed: datetime | None = None
        self.last_summary: dict[str, int] = {}
        self.files_total: int = 0
        self.files_done: int = 0
        self.current_file: str = ""
        self.current_target: str = ""


scan_state = ScanState()
scheduler = BackgroundScheduler(timezone="UTC")


def _progress_callback(target_label: str, file_path: str, done: int, total: int) -> None:
    with scan_state.lock:
        scan_state.current_target = target_label
        scan_state.current_file = os.path.basename(file_path) if file_path else ""
        scan_state.files_done = done
        scan_state.files_total = total


def _run_scan_job() -> None:
    with scan_state.lock:
        if scan_state.running:
            return
        scan_state.running = True
        scan_state.last_started = datetime.utcnow()
        scan_state.files_total = 0
        scan_state.files_done = 0
        scan_state.current_file = ""
        scan_state.current_target = ""

    try:
        with SessionLocal() as session:
            summary = run_full_scan(session, progress_callback=_progress_callback)
        with scan_state.lock:
            scan_state.last_summary = summary
    finally:
        with scan_state.lock:
            scan_state.running = False
            scan_state.last_completed = datetime.utcnow()
            scan_state.current_file = ""
            scan_state.current_target = ""


def start_scheduler(interval_seconds: int) -> None:
    if not scheduler.running:
        scheduler.start()
    reschedule_scan_job(interval_seconds)


def reschedule_scan_job(interval_seconds: int) -> None:
    scheduler.add_job(
        _run_scan_job,
        "interval",
        seconds=max(interval_seconds, 60),
        id="video_scan_job",
        replace_existing=True,
        max_instances=1,
    )


def trigger_manual_scan() -> bool:
    with scan_state.lock:
        if scan_state.running:
            return False
    thread = threading.Thread(target=_run_scan_job, daemon=True)
    thread.start()
    return True


def get_scan_status() -> dict:
    with scan_state.lock:
        return {
            "running": scan_state.running,
            "last_started": scan_state.last_started.isoformat() if scan_state.last_started else None,
            "last_completed": (
                scan_state.last_completed.isoformat() if scan_state.last_completed else None
            ),
            "last_summary": scan_state.last_summary,
            "files_total": scan_state.files_total,
            "files_done": scan_state.files_done,
            "current_file": scan_state.current_file,
            "current_target": scan_state.current_target,
        }
