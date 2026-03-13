from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

from api.schemas import RunsStatsResponse
from api.services.analytics import compute_runs_stats
from core.db import get_session


router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("/stats", response_model=RunsStatsResponse)
def runs_stats(session: Session = Depends(get_session)) -> RunsStatsResponse:
    total_runs, wins, win_rate = compute_runs_stats(session)
    return RunsStatsResponse(total_runs=total_runs, wins=wins, win_rate=win_rate)
