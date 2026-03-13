from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from api.schemas import RecommendationResponse
from api.services.analytics import recommend_card
from core.db import get_session


router = APIRouter(tags=["recommendation"])


@router.get("/recommendation", response_model=RecommendationResponse)
def recommendation(
    cards: str = Query(default="", description="Comma-separated list of offered cards"),
    session: Session = Depends(get_session),
) -> RecommendationResponse:
    offered_cards = [card.strip() for card in cards.split(",") if card.strip()]
    result = recommend_card(session, offered_cards)
    return RecommendationResponse(
        best_pick=result.best_pick,
        win_rate_boost=result.win_rate_boost,
        confidence=result.confidence,
        sample_size=result.sample_size,
        card_win_rate=result.card_win_rate,
        global_win_rate=result.global_win_rate,
        reason=result.reason,
    )
