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
    sample_size: int
    card_win_rate: float
    global_win_rate: float
    reason: str


class CardInsightResponse(BaseModel):
    card: str
    sample_size: int
    card_win_rate: float
    win_rate_boost: float


class CardInsightsResponse(BaseModel):
    global_win_rate: float
    insights: list[CardInsightResponse]


class IngestStatusResponse(BaseModel):
    scanned: int
    imported: int
    updated: int
    parse_errors: int
    skipped: int
