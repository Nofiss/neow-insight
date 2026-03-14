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
    available_direct: int
    available_inferred: int
    total: int
    missing: list[str]
    inferred: list[str]


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


def _flatten_map_points(
    raw_payload: dict[str, Any],
) -> list[tuple[int, dict[str, Any]]]:
    points: list[tuple[int, dict[str, Any]]] = []
    payload = raw_payload.get("map_point_history")
    if not isinstance(payload, list):
        return points

    floor = 0
    for act in payload:
        if not isinstance(act, list):
            continue
        for map_point in act:
            if not isinstance(map_point, dict):
                continue
            floor += 1
            points.append((floor, map_point))
    return points


def _iter_player_stats(map_point: dict[str, Any]) -> list[dict[str, Any]]:
    payload = map_point.get("player_stats")
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


def _extract_event_title(item: dict[str, Any]) -> str | None:
    title = item.get("title")
    if not isinstance(title, dict):
        return None
    key = title.get("key")
    if isinstance(key, str) and key:
        return key
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
    events.extend(_events_from_sts2_payload(raw_payload))
    return events


def _events_from_sts2_payload(raw_payload: dict[str, Any]) -> list[RunTimelineEvent]:
    events: list[RunTimelineEvent] = []
    for floor, map_point in _flatten_map_points(raw_payload):
        map_point_type = map_point.get("map_point_type")
        map_point_type_name = (
            map_point_type if isinstance(map_point_type, str) else "unknown"
        )

        for stats in _iter_player_stats(map_point):
            rest_site_choices = stats.get("rest_site_choices")
            if isinstance(rest_site_choices, list):
                for choice in rest_site_choices:
                    if not isinstance(choice, str) or not choice:
                        continue
                    events.append(
                        RunTimelineEvent(
                            floor=floor,
                            kind="campfire",
                            summary=f"Campfire: {choice}",
                            data={
                                "choice": choice,
                                "map_point_type": map_point_type_name,
                            },
                        )
                    )

            event_choices = stats.get("event_choices")
            if isinstance(event_choices, list):
                for choice in event_choices:
                    if not isinstance(choice, dict):
                        continue
                    event_title = _extract_event_title(choice) or "Unknown Event"
                    events.append(
                        RunTimelineEvent(
                            floor=floor,
                            kind="event",
                            summary=f"Event: {event_title}",
                            data=choice,
                        )
                    )

            potion_choices = stats.get("potion_choices")
            if isinstance(potion_choices, list):
                for choice in potion_choices:
                    if not isinstance(choice, dict):
                        continue
                    potion_id = choice.get("choice")
                    if (
                        choice.get("was_picked") is True
                        and isinstance(potion_id, str)
                        and potion_id
                    ):
                        events.append(
                            RunTimelineEvent(
                                floor=floor,
                                kind="potion",
                                summary=f"Obtained potion {potion_id}",
                                data=choice,
                            )
                        )

            potion_used = stats.get("potion_used")
            if isinstance(potion_used, list):
                for potion_id in potion_used:
                    if not isinstance(potion_id, str) or not potion_id:
                        continue
                    events.append(
                        RunTimelineEvent(
                            floor=floor,
                            kind="potion",
                            summary=f"Used potion {potion_id}",
                            data={"potion_id": potion_id},
                        )
                    )

            relic_choices = stats.get("relic_choices")
            if isinstance(relic_choices, list) and map_point_type_name == "boss":
                for relic_choice in relic_choices:
                    if not isinstance(relic_choice, dict):
                        continue
                    relic_id = relic_choice.get("choice")
                    if (
                        relic_choice.get("was_picked") is True
                        and isinstance(relic_id, str)
                        and relic_id
                    ):
                        events.append(
                            RunTimelineEvent(
                                floor=floor,
                                kind="boss_relic",
                                summary=f"Boss relic pick: {relic_id}",
                                data=relic_choice,
                            )
                        )

    return events


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def resolve_imported_at(raw_timestamp: str | None, imported_at: str | None) -> str:
    normalized_imported_at = _normalize_text(imported_at)
    if normalized_imported_at is not None:
        return normalized_imported_at
    normalized_raw_timestamp = _normalize_text(raw_timestamp)
    if normalized_raw_timestamp is not None:
        return normalized_raw_timestamp
    return "1970-01-01T00:00:00Z"


def _has_payload_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return bool(value)
    return True


def build_run_completeness(raw_payload: dict[str, Any]) -> RunCompleteness:
    derived_values = _derive_sts2_completeness_values(raw_payload)
    missing: list[str] = []
    inferred: list[str] = []
    available_direct = 0
    available_inferred = 0

    for key, label in COMPLETENESS_FIELDS:
        has_direct_value = _has_payload_value(raw_payload.get(key))
        has_inferred_value = key in derived_values

        if has_direct_value:
            available_direct += 1
            continue
        if has_inferred_value:
            available_inferred += 1
            inferred.append(label)
            continue
        missing.append(label)

    total = len(COMPLETENESS_FIELDS)
    return RunCompleteness(
        available=available_direct + available_inferred,
        available_direct=available_direct,
        available_inferred=available_inferred,
        total=total,
        missing=missing,
        inferred=inferred,
    )


def _derive_sts2_completeness_values(raw_payload: dict[str, Any]) -> set[str]:
    derived: set[str] = set()
    map_points = _flatten_map_points(raw_payload)
    if map_points:
        derived.add("floor_reached")

    if _has_payload_value(raw_payload.get("run_time")):
        derived.add("playtime")

    last_stats: dict[str, Any] | None = None
    has_card_choices = False
    has_event_choices = False
    has_campfire_choices = False
    has_potions_obtained = False
    has_boss_relics = False
    gold_samples: list[int] = []
    max_hp_samples: list[int] = []
    current_hp_samples: list[int] = []

    for _, map_point in map_points:
        map_point_type = map_point.get("map_point_type")
        for stats in _iter_player_stats(map_point):
            last_stats = stats
            if _has_payload_value(stats.get("card_choices")):
                has_card_choices = True
            if _has_payload_value(stats.get("event_choices")):
                has_event_choices = True
            if _has_payload_value(stats.get("rest_site_choices")):
                has_campfire_choices = True
            if _has_payload_value(stats.get("potion_choices")):
                has_potions_obtained = True

            relic_choices = stats.get("relic_choices")
            if isinstance(relic_choices, list) and map_point_type == "boss":
                if any(
                    isinstance(item, dict) and item.get("was_picked") is True
                    for item in relic_choices
                ):
                    has_boss_relics = True

            gold_value = _parse_floor(stats.get("current_gold"))
            if gold_value is not None:
                gold_samples.append(gold_value)

            max_hp_value = _parse_floor(stats.get("max_hp"))
            if max_hp_value is not None:
                max_hp_samples.append(max_hp_value)

            current_hp_value = _parse_floor(stats.get("current_hp"))
            if current_hp_value is not None:
                current_hp_samples.append(current_hp_value)

    if gold_samples:
        derived.add("gold")
        derived.add("gold_per_floor")
    if max_hp_samples:
        derived.add("max_hp_per_floor")
    if current_hp_samples:
        derived.add("current_hp_per_floor")
    if has_card_choices:
        derived.add("card_choices")
    if has_event_choices:
        derived.add("event_choices")
    if has_campfire_choices:
        derived.add("campfire_choices")
    if has_potions_obtained:
        derived.add("potions_obtained")
    if has_boss_relics:
        derived.add("boss_relics")

    if last_stats and _has_payload_value(last_stats.get("current_gold")):
        derived.add("gold")

    return derived


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
            imported_at=resolve_imported_at(run.raw_timestamp, run.imported_at),
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


def list_characters(session: Session) -> list[str]:
    rows = session.exec(
        select(col(Run.character))
        .where(col(Run.character).is_not(None))
        .distinct()
        .order_by(col(Run.character).asc())
    ).all()
    return [
        character
        for character in rows
        if isinstance(character, str) and character.strip()
    ]


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
