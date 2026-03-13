from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.results import router as results_router
from app.api.scan import router as scan_router
from app.api.settings import router as settings_router
from app.api.targets import router as targets_router
from app.core.database import SessionLocal, init_db
from app.core.models import Setting
from app.core.scheduler import scheduler, start_scheduler
from app.ui.ui_routes import router as ui_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    with SessionLocal() as session:
        interval_row = session.query(Setting).filter(Setting.key == "scan_interval_seconds").first()
        interval_seconds = int(interval_row.value) if interval_row else 3600
    start_scheduler(interval_seconds)
    yield
    if scheduler.running:
        scheduler.shutdown(wait=False)


app = FastAPI(title="Video Error Checker", lifespan=lifespan)

app.include_router(settings_router)
app.include_router(targets_router)
app.include_router(results_router)
app.include_router(scan_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


app.include_router(ui_router)
