from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from sqlmodel import Session, col, func, select

from core.db.models import CardChoice, RelicHistory, Run


@dataclass(frozen=True)
class RunListFilters:
    page: int
    page_size: int
    character: str | None
    ascension: int | None
    win: bool | None
    query: str | None


@dataclass(frozen=True)
class RunListItem:
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


@dataclass(frozen=True)
class RunListResult:
    page: int
    page_size: int
    total: int
    total_pages: int
    items: list[RunListItem]


@dataclass(frozen=True)
class RunDetail:
    run: Run
    card_choices: list[CardChoice]
    relic_history: list[RelicHistory]


@dataclass(frozen=True)
class RunTimelineEvent:
    floor: int
    kind: str
    summary: str
    data: dict[str, Any]


@dataclass(frozen=True)
class RunCompleteness:
    available: int
    total: int
    missing: list[str]


COMPLETENESS_FIELDS: tuple[tuple[str, str], ...] = (
    ("score", "Score"),
    ("floor_reached", "Floor reached"),
    ("gold", "Gold"),
    ("gold_per_floor", "Gold per floor"),
    ("playtime", "Playtime"),
    ("max_hp_per_floor", "Max HP per floor"),
    ("current_hp_per_floor", "Current HP per floor"),
    ("campfire_choices", "Campfire choices"),
    ("event_choices", "Event choices"),
    ("card_choices", "Card choices"),
    ("boss_relics", "Boss relics"),
    ("potions_obtained", "Potions obtained"),
)


def _parse_floor(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def _events_from_campfire_choices(
    raw_payload: dict[str, Any],
) -> list[RunTimelineEvent]:
    events: list[RunTimelineEvent] = []
    payload = raw_payload.get("campfire_choices")
    if not isinstance(payload, list):
        return events

    for item in payload:
        if not isinstance(item, dict):
            continue
        floor = _parse_floor(item.get("floor"))
        if floor is None:
            continue
        action = item.get("key")
        if not isinstance(action, str) or not action:
            action = "UNKNOWN"
        events.append(
            RunTimelineEvent(
                floor=floor,
                kind="campfire",
                summary=f"Campfire: {action}",
                data=item,
            )
        )
    return events


def _events_from_event_choices(raw_payload: dict[str, Any]) -> list[RunTimelineEvent]:
    events: list[RunTimelineEvent] = []
    payload = raw_payload.get("event_choices")
    if not isinstance(payload, list):
        return events

    for item in payload:
        if not isinstance(item, dict):
            continue
        floor = _parse_floor(item.get("floor"))
        if floor is None:
            continue
        event_name = item.get("event_name")
        if not isinstance(event_name, str) or not event_name:
            event_name = "Unknown Event"
        player_choice = item.get("player_choice")
        if isinstance(player_choice, str) and player_choice:
            summary = f"Event: {event_name} ({player_choice})"
        else:
            summary = f"Event: {event_name}"
        events.append(
            RunTimelineEvent(
                floor=floor,
                kind="event",
                summary=summary,
                data=item,
            )
        )
    return events


def _events_from_potions_obtained(
    raw_payload: dict[str, Any],
) -> list[RunTimelineEvent]:
    events: list[RunTimelineEvent] = []
    payload = raw_payload.get("potions_obtained")
    if not isinstance(payload, list):
        return events

    for item in payload:
        if not isinstance(item, dict):
            continue
        floor = _parse_floor(item.get("floor"))
        potion = item.get("key")
        if floor is None or not isinstance(potion, str) or not potion:
            continue
        events.append(
            RunTimelineEvent(
                floor=floor,
                kind="potion",
                summary=f"Obtained potion {potion}",
                data=item,
            )
        )
    return events


def _events_from_boss_relic_choices(
    raw_payload: dict[str, Any],
) -> list[RunTimelineEvent]:
    events: list[RunTimelineEvent] = []
    payload = raw_payload.get("boss_relics")
    if not isinstance(payload, list):
        return events

    for item in payload:
        if not isinstance(item, dict):
            continue
        picked = item.get("picked")
        if not isinstance(picked, str) or not picked:
            continue
        events.append(
            RunTimelineEvent(
                floor=999,
                kind="boss_relic",
                summary=f"Boss relic pick: {picked}",
                data=item,
            )
        )
    return events


def _events_from_raw_payload(raw_payload: dict[str, Any]) -> list[RunTimelineEvent]:
    events: list[RunTimelineEvent] = []
    events.extend(_events_from_campfire_choices(raw_payload))
    events.extend(_events_from_event_choices(raw_payload))
    events.extend(_events_from_potions_obtained(raw_payload))
    events.extend(_events_from_boss_relic_choices(raw_payload))
    return events


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _has_payload_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return bool(value)
    return True


def build_run_completeness(raw_payload: dict[str, Any]) -> RunCompleteness:
    missing = [
        label
        for key, label in COMPLETENESS_FIELDS
        if not _has_payload_value(raw_payload.get(key))
    ]
    total = len(COMPLETENESS_FIELDS)
    return RunCompleteness(available=total - len(missing), total=total, missing=missing)


def _base_runs_query(filters: RunListFilters):
    query = select(Run)
    character = _normalize_text(filters.character)
    if character:
        query = query.where(col(Run.character) == character.upper())
    if filters.ascension is not None:
        query = query.where(col(Run.ascension) == filters.ascension)
    if filters.win is not None:
        query = query.where(col(Run.win) == filters.win)

    search_query = _normalize_text(filters.query)
    if search_query:
        like_value = f"%{search_query}%"
        query = query.where(
            col(Run.id).like(like_value)
            | col(Run.character).like(like_value)
            | col(Run.seed).like(like_value)
        )
    return query


def list_runs(session: Session, filters: RunListFilters) -> RunListResult:
    page = max(1, filters.page)
    page_size = min(max(1, filters.page_size), 200)

    base_query = _base_runs_query(filters)
    total = int(
        session.exec(select(func.count()).select_from(base_query.subquery())).one()
    )
    total_pages = max(1, math.ceil(total / page_size)) if total else 1
    page = min(page, total_pages)
    offset = (page - 1) * page_size

    runs = session.exec(
        base_query.order_by(col(Run.raw_timestamp).desc(), col(Run.imported_at).desc())
        .offset(offset)
        .limit(page_size)
    ).all()

    run_ids = [item.id for item in runs]
    card_counts = _count_card_choices(session, run_ids)
    relic_counts = _count_relics(session, run_ids)
    items = [
        RunListItem(
            run_id=run.id,
            seed=run.seed,
            character=run.character,
            ascension=run.ascension,
            win=run.win,
            raw_timestamp=run.raw_timestamp,
            imported_at=run.imported_at,
            source_file=run.source_file,
            card_choice_count=card_counts.get(run.id, 0),
            relic_count=relic_counts.get(run.id, 0),
        )
        for run in runs
    ]

    return RunListResult(
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
        items=items,
    )


def _count_card_choices(session: Session, run_ids: list[str]) -> dict[str, int]:
    if not run_ids:
        return {}
    rows = session.exec(
        select(col(CardChoice.run_id), func.count())
        .where(col(CardChoice.run_id).in_(run_ids))
        .group_by(col(CardChoice.run_id))
    ).all()
    return {str(run_id): int(count) for run_id, count in rows}


def _count_relics(session: Session, run_ids: list[str]) -> dict[str, int]:
    if not run_ids:
        return {}
    rows = session.exec(
        select(col(RelicHistory.run_id), func.count())
        .where(col(RelicHistory.run_id).in_(run_ids))
        .group_by(col(RelicHistory.run_id))
    ).all()
    return {str(run_id): int(count) for run_id, count in rows}


def get_run_detail(session: Session, run_id: str) -> RunDetail | None:
    run = session.get(Run, run_id)
    if run is None:
        return None
    card_choices = session.exec(
        select(CardChoice)
        .where(col(CardChoice.run_id) == run_id)
        .order_by(col(CardChoice.floor).asc(), col(CardChoice.id).asc())
    ).all()
    relic_history = session.exec(
        select(RelicHistory)
        .where(col(RelicHistory.run_id) == run_id)
        .order_by(col(RelicHistory.floor).asc(), col(RelicHistory.id).asc())
    ).all()
    card_choices_result = list(card_choices)
    relic_history_result = list(relic_history)
    return RunDetail(
        run=run, card_choices=card_choices_result, relic_history=relic_history_result
    )


def get_run_completeness(session: Session, run_id: str) -> RunCompleteness | None:
    run = session.get(Run, run_id)
    if run is None:
        return None
    return build_run_completeness(run.raw_payload or {})


def build_run_timeline(detail: RunDetail) -> list[RunTimelineEvent]:
    events: list[RunTimelineEvent] = []

    for choice in detail.card_choices:
        events.append(
            RunTimelineEvent(
                floor=choice.floor,
                kind="card_choice",
                summary=f"Picked {choice.picked_card}",
                data={
                    "picked_card": choice.picked_card,
                    "offered_cards": list(choice.offered_cards),
                    "is_shop": choice.is_shop,
                },
            )
        )

    for relic in detail.relic_history:
        events.append(
            RunTimelineEvent(
                floor=relic.floor,
                kind="relic",
                summary=f"Obtained relic {relic.relic_id}",
                data={"relic_id": relic.relic_id},
            )
        )

    events.extend(_events_from_raw_payload(detail.run.raw_payload or {}))

    events.sort(key=lambda item: (item.floor, item.kind))
    return events
