from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

from api.schemas import CardInsightResponse, CardInsightsResponse, RunsStatsResponse
from api.services.analytics import compute_card_insights, compute_runs_stats
from core.db import get_session


router = APIRouter(prefix="/runs", tags=["runs-stats"])


@router.get("/stats", response_model=RunsStatsResponse)
def runs_stats(session: Session = Depends(get_session)) -> RunsStatsResponse:
    total_runs, wins, win_rate = compute_runs_stats(session)
    return RunsStatsResponse(total_runs=total_runs, wins=wins, win_rate=win_rate)


@router.get("/card-insights", response_model=CardInsightsResponse)
def card_insights(
    cards: str = "",
    session: Session = Depends(get_session),
) -> CardInsightsResponse:
    offered_cards = list(
        dict.fromkeys(card.strip() for card in cards.split(",") if card.strip())
    )
    global_win_rate, insights = compute_card_insights(session, offered_cards)
    return CardInsightsResponse(
        global_win_rate=global_win_rate,
        insights=[
            CardInsightResponse(
                card=item.card,
                sample_size=item.sample_size,
                card_win_rate=item.card_win_rate,
                win_rate_boost=item.win_rate_boost,
            )
            for item in insights
        ],
    )
