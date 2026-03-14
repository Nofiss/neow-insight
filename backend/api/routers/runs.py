from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from api.schemas import (
    RunCompletenessResponse,
    RunCardChoiceResponse,
    RunDetailResponse,
    RunListItemResponse,
    RunRelicResponse,
    RunsListResponse,
    RunTimelineEventResponse,
    RunTimelineResponse,
)
from api.services.runs_history import (
    RunListFilters,
    build_run_timeline,
    get_run_completeness,
    get_run_detail,
    list_runs,
    resolve_imported_at,
)
from core.db import get_session


router = APIRouter(prefix="/runs", tags=["runs-history"])


@router.get("", response_model=RunsListResponse)
def runs_list(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    character: str | None = Query(default=None),
    ascension: int | None = Query(default=None, ge=0),
    win: bool | None = Query(default=None),
    query: str | None = Query(default=None),
    session: Session = Depends(get_session),
) -> RunsListResponse:
    result = list_runs(
        session,
        RunListFilters(
            page=page,
            page_size=page_size,
            character=character,
            ascension=ascension,
            win=win,
            query=query,
        ),
    )
    return RunsListResponse(
        page=result.page,
        page_size=result.page_size,
        total=result.total,
        total_pages=result.total_pages,
        items=[
            RunListItemResponse(
                run_id=item.run_id,
                seed=item.seed,
                character=item.character,
                ascension=item.ascension,
                win=item.win,
                raw_timestamp=item.raw_timestamp,
                imported_at=item.imported_at,
                source_file=item.source_file,
                card_choice_count=item.card_choice_count,
                relic_count=item.relic_count,
            )
            for item in result.items
        ],
    )


@router.get("/{run_id}", response_model=RunDetailResponse)
def run_detail(
    run_id: str, session: Session = Depends(get_session)
) -> RunDetailResponse:
    detail = get_run_detail(session, run_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="run not found")
    return RunDetailResponse(
        run_id=detail.run.id,
        seed=detail.run.seed,
        character=detail.run.character,
        ascension=detail.run.ascension,
        win=detail.run.win,
        raw_timestamp=detail.run.raw_timestamp,
        imported_at=resolve_imported_at(
            detail.run.raw_timestamp,
            detail.run.imported_at,
        ),
        source_file=detail.run.source_file,
        card_choices=[
            RunCardChoiceResponse(
                floor=item.floor,
                offered_cards=list(item.offered_cards),
                picked_card=item.picked_card,
                is_shop=item.is_shop,
            )
            for item in detail.card_choices
        ],
        relic_history=[
            RunRelicResponse(relic_id=item.relic_id, floor=item.floor)
            for item in detail.relic_history
        ],
        raw_payload=detail.run.raw_payload or {},
    )


@router.get("/{run_id}/timeline", response_model=RunTimelineResponse)
def run_timeline(
    run_id: str, session: Session = Depends(get_session)
) -> RunTimelineResponse:
    detail = get_run_detail(session, run_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="run not found")
    timeline = build_run_timeline(detail)
    return RunTimelineResponse(
        run_id=run_id,
        events=[
            RunTimelineEventResponse(
                floor=item.floor,
                kind=item.kind,
                summary=item.summary,
                data=item.data,
            )
            for item in timeline
        ],
    )


@router.get("/{run_id}/completeness", response_model=RunCompletenessResponse)
def run_completeness(
    run_id: str, session: Session = Depends(get_session)
) -> RunCompletenessResponse:
    result = get_run_completeness(session, run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="run not found")
    return RunCompletenessResponse(
        run_id=run_id,
        available=result.available,
        available_direct=result.available_direct,
        available_inferred=result.available_inferred,
        total=result.total,
        missing=result.missing,
        inferred=result.inferred,
    )
