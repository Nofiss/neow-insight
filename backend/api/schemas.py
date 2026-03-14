from __future__ import annotations

from typing import Any

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


class RunCardChoiceResponse(BaseModel):
    floor: int
    offered_cards: list[str]
    picked_card: str
    is_shop: bool


class RunRelicResponse(BaseModel):
    relic_id: str
    floor: int


class RunListItemResponse(BaseModel):
    run_id: str
    seed: str | None
    character: str | None
    ascension: int | None
    win: bool
    raw_timestamp: str | None
    imported_at: str
    source_file: str | None
    card_choice_count: int
    relic_count: int


class RunsListResponse(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int
    items: list[RunListItemResponse]


class RunCharactersResponse(BaseModel):
    items: list[str]


class RunDetailResponse(BaseModel):
    run_id: str
    seed: str | None
    character: str | None
    ascension: int | None
    win: bool
    raw_timestamp: str | None
    imported_at: str
    source_file: str | None
    card_choices: list[RunCardChoiceResponse]
    relic_history: list[RunRelicResponse]
    raw_payload: dict[str, Any]


class RunTimelineEventResponse(BaseModel):
    floor: int
    kind: str
    summary: str
    data: dict[str, Any]


class RunTimelineResponse(BaseModel):
    run_id: str
    events: list[RunTimelineEventResponse]


class RunCompletenessResponse(BaseModel):
    run_id: str
    available: int
    available_direct: int
    available_inferred: int
    total: int
    missing: list[str]
    inferred: list[str]
