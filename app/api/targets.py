import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.models import ScanTarget


router = APIRouter(prefix="/api/targets", tags=["targets"])
MEDIA_ROOT = Path("/media").resolve()


class TargetCreate(BaseModel):
    label: str
    path: str
    enabled: bool = True


class TargetUpdate(BaseModel):
    label: str
    path: str
    enabled: bool = True


@router.get("")
def list_targets(db: Session = Depends(get_db)) -> list[dict]:
    targets = db.query(ScanTarget).order_by(ScanTarget.label.asc()).all()
    return [
        {"id": item.id, "label": item.label, "path": item.path, "enabled": item.enabled}
        for item in targets
    ]


@router.post("")
def create_target(payload: TargetCreate, db: Session = Depends(get_db)) -> dict:
    target = ScanTarget(label=payload.label, path=payload.path, enabled=payload.enabled)
    db.add(target)
    db.commit()
    db.refresh(target)
    return {"id": target.id}


@router.put("/{target_id}")
def update_target(target_id: int, payload: TargetUpdate, db: Session = Depends(get_db)) -> dict:
    target = db.query(ScanTarget).filter(ScanTarget.id == target_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")

    target.label = payload.label
    target.path = payload.path
    target.enabled = payload.enabled
    db.commit()
    return {"status": "updated"}


@router.delete("/{target_id}")
def delete_target(target_id: int, db: Session = Depends(get_db)) -> dict:
    target = db.query(ScanTarget).filter(ScanTarget.id == target_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    db.delete(target)
    db.commit()
    return {"status": "deleted"}


@router.get("/browse")
def browse_directories(path: str | None = None) -> dict:
    requested = Path(path or "/media").resolve()

    if requested != MEDIA_ROOT and MEDIA_ROOT not in requested.parents:
        raise HTTPException(status_code=400, detail="Path must be under /media")
    if not requested.exists() or not requested.is_dir():
        raise HTTPException(status_code=404, detail="Directory not found")

    children: list[dict[str, str]] = []
    for entry in sorted(os.scandir(requested), key=lambda item: item.name.lower()):
        if entry.is_dir():
            children.append({"name": entry.name, "path": str(Path(entry.path).resolve())})

    parent = requested.parent if requested != MEDIA_ROOT else requested
    return {
        "path": str(requested),
        "parent": str(parent),
        "directories": children,
    }
