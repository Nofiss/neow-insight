from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

from api.schemas import (
    LiveContextResponse,
    LiveRecoverCardsRequest,
    LiveRecoverCardsResponse,
)
from api.services.live_card_recovery import recover_live_cards
from api.services.live_context import get_live_context
from core.config import get_settings
from core.db import get_session


router = APIRouter(prefix="/live", tags=["live"])
settings = get_settings()


@router.get("/context", response_model=LiveContextResponse)
def live_context(session: Session = Depends(get_session)) -> LiveContextResponse:
    context = get_live_context(session)
    return LiveContextResponse(
        available=context.available,
        run_id=context.run_id,
        character=context.character,
        ascension=context.ascension,
        floor=context.floor,
        offered_cards=context.offered_cards,
        picked_card=context.picked_card,
    )


@router.post("/recover-cards", response_model=LiveRecoverCardsResponse)
def live_recover_cards(
    payload: LiveRecoverCardsRequest,
    session: Session = Depends(get_session),
) -> LiveRecoverCardsResponse:
    result = recover_live_cards(
        session=session,
        settings=settings,
        image_base64=payload.image_base64,
    )
    return LiveRecoverCardsResponse(
        success=result.success,
        offered_cards=result.offered_cards,
        source=result.source,
        llm_model=result.llm_model,
        llm_error=result.llm_error,
    )
