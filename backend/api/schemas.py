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
    scope: str
    applied_filters: list[str]
    fallback_used: bool


class CardInsightResponse(BaseModel):
    card: str
    sample_size: int
    card_win_rate: float
    win_rate_boost: float


class CardInsightsResponse(BaseModel):
    global_win_rate: float
    insights: list[CardInsightResponse]


class IngestIssueResponse(BaseModel):
    kind: str
    file_path: str
    message: str
    timestamp: str


class IngestStatusResponse(BaseModel):
    scanned: int
    imported: int
    updated: int
    parse_errors: int
    skipped: int
    recent_issues: list[IngestIssueResponse]
    last_processed_run_id: str | None
    last_processed_file: str | None
    last_event_at: str | None


class LiveContextResponse(BaseModel):
    available: bool
    run_id: str | None
    character: str | None
    ascension: int | None
    floor: int | None
    offered_cards: list[str]
    picked_card: str | None
