from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.models import ScanResult, ScanTarget


router = APIRouter(prefix="/api/results", tags=["results"])


@router.get("")
def list_results(
    db: Session = Depends(get_db),
    label: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=2000),
) -> list[dict]:
    query = db.query(ScanResult, ScanTarget.label).join(ScanTarget, ScanTarget.id == ScanResult.target_id)
    if label:
        query = query.filter(ScanTarget.label == label)
    if status:
        query = query.filter(ScanResult.status == status)

    rows = query.order_by(ScanResult.scanned_at.desc()).limit(limit).all()
    return [
        {
            "id": result.id,
            "label": target_label,
            "file_path": result.file_path,
            "last_modified": result.last_modified,
            "status": result.status,
            "details": result.details,
            "scan_duration_seconds": result.scan_duration_seconds,
            "scanned_at": result.scanned_at.isoformat(),
        }
        for result, target_label in rows
    ]


@router.get("/summary")
def get_summary(db: Session = Depends(get_db)) -> dict:
    grouped = (
        db.query(ScanTarget.label, ScanResult.status, func.count(ScanResult.id))
        .join(ScanResult, ScanTarget.id == ScanResult.target_id)
        .group_by(ScanTarget.label, ScanResult.status)
        .all()
    )

    summary: dict[str, dict[str, int]] = {}
    for label, status, count in grouped:
        summary.setdefault(label, {})
        summary[label][status] = int(count)

    latest_scan = db.query(func.max(ScanResult.scanned_at)).scalar()
    return {
        "by_target": summary,
        "last_scan": latest_scan.isoformat() if isinstance(latest_scan, datetime) else None,
    }
