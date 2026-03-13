from fastapi import APIRouter

from app.core.scheduler import get_scan_status, trigger_manual_scan


router = APIRouter(prefix="/api/scan", tags=["scan"])


@router.post("/trigger")
def trigger_scan() -> dict:
    started = trigger_manual_scan()
    if not started:
        return {"status": "already-running"}
    return {"status": "started"}


@router.get("/status")
def scan_status() -> dict:
    return get_scan_status()
