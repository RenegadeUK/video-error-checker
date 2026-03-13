from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse, JSONResponse


router = APIRouter()
static_root = Path(__file__).resolve().parent / "static" / "app"


@router.get("/assets/{asset_path:path}")
def assets(asset_path: str):
    asset_file = static_root / "assets" / asset_path
    if asset_file.exists() and asset_file.is_file():
        return FileResponse(str(asset_file))
    return JSONResponse({"detail": "Not Found"}, status_code=404)


@router.get("/")
def index():
    index_path = static_root / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return JSONResponse({"message": "UI build not found. Build ui-react and copy dist to app/ui/static/app."})


@router.get("/{full_path:path}")
def spa_catch_all(full_path: str):
    if full_path.startswith("api/") or full_path.startswith("assets/"):
        return JSONResponse({"detail": "Not Found"}, status_code=404)

    index_path = static_root / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return JSONResponse({"message": "UI build not found."}, status_code=404)
