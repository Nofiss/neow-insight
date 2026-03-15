from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import desc
from sqlmodel import Session, col, func, select

from api.services.analytics import (
    RecommendationContext,
    RecommendationResult,
    recommend_card,
)
from api.services.live_context import get_live_context
from core.config import Settings
from core.db.models import Run
from core.llm import LlmClient, LlmClientError


SYSTEM_PROMPT = (
    "You are an expert Slay the Spire run analyst. "
    "Given run context and offered cards, return only compact JSON. "
    "Never add markdown."
)


class LlmRecommendationPayload(BaseModel):
    llm_pick: str | None = None
    rationale: str = ""
    strategy_tags: list[str] = Field(default_factory=list)
    confidence: float | None = None


@dataclass
class LiveHybridRecommendationResult:
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
    llm_pick: str | None
    llm_rationale: str | None
    llm_strategy_tags: list[str]
    llm_confidence: float | None
    llm_model: str | None
    llm_used: bool
    llm_error: str | None
    source: str


_LLM_CACHE: dict[
    str, tuple[LlmRecommendationPayload | None, str | None, str | None]
] = {}


def _build_run_recency_expr():
    return func.coalesce(
        func.nullif(col(Run.imported_at), ""),
        func.nullif(col(Run.raw_timestamp), ""),
        "1970-01-01T00:00:00Z",
    )


def _get_latest_run_payload(session: Session) -> tuple[str | None, dict[str, Any]]:
    run_recency = _build_run_recency_expr()
    run = session.exec(
        select(Run).order_by(desc(run_recency), desc(col(Run.id))).limit(1)
    ).first()
    if run is None:
        return None, {}
    payload = run.raw_payload if isinstance(run.raw_payload, dict) else {}
    return run.id, payload


def _build_prompt(
    *,
    run_id: str,
    offered_cards: list[str],
    character: str | None,
    ascension: int | None,
    floor: int | None,
    raw_payload: dict[str, Any],
) -> str:
    reduced_payload = {
        "run_id": raw_payload.get("run_id"),
        "floor_reached": raw_payload.get("floor_reached"),
        "score": raw_payload.get("score"),
        "gold": raw_payload.get("gold"),
        "map_point_history": raw_payload.get("map_point_history"),
        "card_choices": raw_payload.get("card_choices"),
        "relics_obtained": raw_payload.get("relics_obtained"),
        "players": raw_payload.get("players"),
    }

    envelope = {
        "run_id": run_id,
        "character": character,
        "ascension": ascension,
        "floor": floor,
        "offered_cards": offered_cards,
        "raw_payload": reduced_payload,
        "instructions": {
            "task": "Recommend one card among offered_cards",
            "constraints": [
                "Pick must be one of offered_cards",
                "Keep rationale <= 220 chars",
                "strategy_tags max 4 tags",
                "confidence between 0 and 1",
            ],
            "output_schema": {
                "llm_pick": "string|null",
                "rationale": "string",
                "strategy_tags": ["string"],
                "confidence": "number|null",
            },
        },
    }
    return json.dumps(envelope, ensure_ascii=True, separators=(",", ":"))


def _coerce_llm_payload(
    payload: LlmRecommendationPayload, offered_cards: list[str]
) -> LlmRecommendationPayload:
    llm_pick = payload.llm_pick if payload.llm_pick in offered_cards else None
    rationale = payload.rationale.strip()
    if len(rationale) > 220:
        rationale = rationale[:220].rstrip()

    deduped_tags: list[str] = []
    for tag in payload.strategy_tags:
        cleaned = tag.strip()
        if not cleaned:
            continue
        if cleaned in deduped_tags:
            continue
        deduped_tags.append(cleaned)
        if len(deduped_tags) >= 4:
            break

    confidence = payload.confidence
    if confidence is not None:
        confidence = min(max(confidence, 0.0), 1.0)

    return LlmRecommendationPayload(
        llm_pick=llm_pick,
        rationale=rationale,
        strategy_tags=deduped_tags,
        confidence=confidence,
    )


def _get_llm_recommendation(
    *,
    settings: Settings,
    run_id: str,
    offered_cards: list[str],
    character: str | None,
    ascension: int | None,
    floor: int | None,
    raw_payload: dict[str, Any],
) -> tuple[LlmRecommendationPayload | None, str | None, str | None]:
    if not settings.llm_enabled:
        return None, None, "llm_disabled"
    if settings.llm_provider != "ollama":
        return None, None, "llm_provider_not_supported"

    cache_key = f"{run_id}|{floor}|{','.join(offered_cards)}"
    if cache_key in _LLM_CACHE:
        cached_payload, cached_model, cached_error = _LLM_CACHE[cache_key]
        return cached_payload, cached_model, cached_error

    prompt = _build_prompt(
        run_id=run_id,
        offered_cards=offered_cards,
        character=character,
        ascension=ascension,
        floor=floor,
        raw_payload=raw_payload,
    )
    client = LlmClient(
        base_url=settings.llm_base_url,
        model=settings.llm_model,
        timeout_ms=settings.llm_timeout_ms,
    )

    try:
        llm_response = client.complete_json(prompt=prompt, system_prompt=SYSTEM_PROMPT)
        parsed = LlmRecommendationPayload.model_validate(llm_response.payload)
        normalized = _coerce_llm_payload(parsed, offered_cards)
        result: tuple[LlmRecommendationPayload | None, str | None, str | None] = (
            normalized,
            llm_response.model,
            None,
        )
        _LLM_CACHE[cache_key] = result
        return result
    except (LlmClientError, ValidationError) as exc:
        error_code = str(exc)
        result = (None, settings.llm_model, error_code)
        _LLM_CACHE[cache_key] = result
        return result


def _from_statistical_result(
    result: RecommendationResult,
) -> LiveHybridRecommendationResult:
    return LiveHybridRecommendationResult(
        best_pick=result.best_pick,
        win_rate_boost=result.win_rate_boost,
        confidence=result.confidence,
        sample_size=result.sample_size,
        card_win_rate=result.card_win_rate,
        global_win_rate=result.global_win_rate,
        reason=result.reason,
        scope=result.scope,
        applied_filters=result.applied_filters,
        fallback_used=result.fallback_used,
        llm_pick=None,
        llm_rationale=None,
        llm_strategy_tags=[],
        llm_confidence=None,
        llm_model=None,
        llm_used=False,
        llm_error=None,
        source="statistical",
    )


def recommend_live_hybrid(
    session: Session, settings: Settings
) -> LiveHybridRecommendationResult:
    live_context = get_live_context(session)
    offered_cards = list(live_context.offered_cards)
    context = RecommendationContext(
        character=live_context.character,
        ascension=live_context.ascension,
        floor=live_context.floor,
    )
    statistical_result = recommend_card(session, offered_cards, context=context)
    base = _from_statistical_result(statistical_result)

    if not live_context.available or not offered_cards:
        return base

    run_id, raw_payload = _get_latest_run_payload(session)
    if not run_id:
        return base

    llm_payload, llm_model, llm_error = _get_llm_recommendation(
        settings=settings,
        run_id=run_id,
        offered_cards=offered_cards,
        character=live_context.character,
        ascension=live_context.ascension,
        floor=live_context.floor,
        raw_payload=raw_payload,
    )
    if llm_payload is None:
        base.llm_model = llm_model
        base.llm_error = llm_error
        base.source = "hybrid_fallback"
        return base

    base.llm_pick = llm_payload.llm_pick
    base.llm_rationale = llm_payload.rationale or None
    base.llm_strategy_tags = llm_payload.strategy_tags
    base.llm_confidence = llm_payload.confidence
    base.llm_model = llm_model
    base.llm_error = None
    base.llm_used = True
    base.source = "hybrid"
    return base
