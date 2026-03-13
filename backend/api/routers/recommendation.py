from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from api.schemas import RecommendationResponse
from api.services.analytics import RecommendationContext, recommend_card
from core.db import get_session


router = APIRouter(tags=["recommendation"])
logger = logging.getLogger(__name__)


@router.get("/recommendation", response_model=RecommendationResponse)
def recommendation(
    cards: str = Query(default="", description="Comma-separated list of offered cards"),
    character: str | None = Query(default=None, description="Character code"),
    ascension: int | None = Query(default=None, ge=0, description="Ascension level"),
    floor: int | None = Query(default=None, ge=0, description="Current floor"),
    session: Session = Depends(get_session),
) -> RecommendationResponse:
    offered_cards = [card.strip() for card in cards.split(",") if card.strip()]
    result = recommend_card(
        session,
        offered_cards,
        context=RecommendationContext(
            character=character,
            ascension=ascension,
            floor=floor,
        ),
    )
    logger.info(
        "recommendation computed reason=%s scope=%s sample_size=%d",
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
    )
