from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from api.schemas import RecommendationResponse
from api.services.analytics import RecommendationContext, recommend_card
from api.services.live_context import get_live_context
from api.services.live_recommendation import recommend_live_hybrid
from core.config import get_settings
from core.db import get_session


router = APIRouter(tags=["recommendation"])
logger = logging.getLogger(__name__)
settings = get_settings()


@router.get("/recommendation", response_model=RecommendationResponse)
def recommendation(
    cards: str = Query(default="", description="Comma-separated list of offered cards"),
    character: str | None = Query(default=None, description="Character code"),
    ascension: int | None = Query(default=None, ge=0, description="Ascension level"),
    floor: int | None = Query(default=None, ge=0, description="Current floor"),
    session: Session = Depends(get_session),
) -> RecommendationResponse:
    offered_cards = [card.strip() for card in cards.split(",") if card.strip()]
    normalized_character = character.strip() if character else None
    normalized_character = (
        normalized_character.upper() if normalized_character else None
    )
    requested_context = RecommendationContext(
        character=normalized_character,
        ascension=ascension,
        floor=floor,
    )

    live_context = get_live_context(session)
    live_character = (
        live_context.character.strip().upper() if live_context.character else None
    )
    live_request_match = (
        live_context.available
        and bool(live_context.offered_cards)
        and offered_cards == live_context.offered_cards
        and normalized_character == live_character
        and ascension == live_context.ascension
        and floor == live_context.floor
    )

    if live_request_match:
        result_payload = recommend_live_hybrid(session, settings)
        logger.info(
            "recommendation computed reason=%s scope=%s sample_size=%d source=%s llm_used=%s",
            result_payload.reason,
            result_payload.scope,
            result_payload.sample_size,
            result_payload.source,
            result_payload.llm_used,
        )
        return RecommendationResponse(
            best_pick=result_payload.best_pick,
            win_rate_boost=result_payload.win_rate_boost,
            confidence=result_payload.confidence,
            sample_size=result_payload.sample_size,
            card_win_rate=result_payload.card_win_rate,
            global_win_rate=result_payload.global_win_rate,
            reason=result_payload.reason,
            scope=result_payload.scope,
            applied_filters=result_payload.applied_filters,
            fallback_used=result_payload.fallback_used,
            llm_pick=result_payload.llm_pick,
            llm_rationale=result_payload.llm_rationale,
            llm_strategy_tags=result_payload.llm_strategy_tags,
            llm_confidence=result_payload.llm_confidence,
            llm_model=result_payload.llm_model,
            llm_used=result_payload.llm_used,
            llm_error=result_payload.llm_error,
            source=result_payload.source,
        )

    result = recommend_card(session, offered_cards, context=requested_context)
    logger.info(
        "recommendation computed reason=%s scope=%s sample_size=%d source=statistical llm_used=false",
        result.reason,
        result.scope,
        result.sample_size,
    )
    return RecommendationResponse(
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
