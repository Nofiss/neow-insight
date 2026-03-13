from __future__ import annotations

from fastapi import APIRouter

from api.schemas import HealthResponse
from core.config import get_settings


router = APIRouter(tags=["health"])
settings = get_settings()


@router.get("/health", response_model=HealthResponse)
def healthcheck() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version="0.1.0",
        watcher_enabled=settings.enable_watcher,
    )
