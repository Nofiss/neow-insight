from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

from api.schemas import LiveContextResponse
from api.services.live_context import get_live_context
from core.db import get_session


router = APIRouter(prefix="/live", tags=["live"])


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
