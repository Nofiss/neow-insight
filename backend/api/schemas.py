from __future__ import annotations

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    version: str
    watcher_enabled: bool


class RunsStatsResponse(BaseModel):
    total_runs: int
    wins: int
    win_rate: float


class RecommendationResponse(BaseModel):
    best_pick: str | None
    win_rate_boost: float
    confidence: float


class IngestStatusResponse(BaseModel):
    scanned: int
    imported: int
    updated: int
    parse_errors: int
    skipped: int
