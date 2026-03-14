from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from api.routers.health import router as health_router
from api.routers.ingest import router as ingest_router
from api.routers.live import router as live_router
from api.routers.recommendation import router as recommendation_router
from api.routers.runs import router as runs_router
from api.routers.stats import router as stats_router
from api.state import apply_import_report
from core.config import get_settings
from core.db import init_db
from core.db.session import engine
from core.ingestion.importer import ImportReport, import_history, import_run_file
from core.watcher import start_watcher
from sqlmodel import Session


settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    observer = None
    init_db()
    with Session(engine) as session:
        startup_report = ImportReport()
        if settings.run_history_path.exists():
            startup_report.absorb(import_history(settings.run_history_path, session))
        if settings.current_run_path.exists():
            startup_report.absorb(import_run_file(settings.current_run_path, session))
        apply_import_report(startup_report)

    if settings.enable_watcher:

        def on_change(_path: Path) -> None:
            with Session(engine) as watcher_session:
                watcher_report = import_run_file(_path, watcher_session)
                apply_import_report(watcher_report)

        observer = start_watcher(
            settings.run_history_path,
            settings.current_run_path,
            on_change=on_change,
            debounce_seconds=settings.watcher_debounce_seconds,
        )
    yield
    if observer is not None:
        observer.stop()
        observer.join()


app = FastAPI(title="Neow Insight API", version="0.1.0", lifespan=lifespan)
app.include_router(health_router)
app.include_router(stats_router)
app.include_router(runs_router)
app.include_router(recommendation_router)
app.include_router(ingest_router)
app.include_router(live_router)
