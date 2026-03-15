from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import desc
from sqlmodel import Session, col, func, select

from core.db.models import CardChoice, Run


@dataclass
class LiveContextResult:
    available: bool
    run_id: str | None
    character: str | None
    ascension: int | None
    floor: int | None
    offered_cards: list[str]
    picked_card: str | None


def _parse_int(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def _count_map_points(payload: Any) -> int:
    if not isinstance(payload, list):
        return 0

    floor = 0
    for act in payload:
        if not isinstance(act, list):
            continue
        for map_point in act:
            if not isinstance(map_point, dict):
                continue
            floor += 1
    return floor


def _resolve_live_floor(
    raw_payload: dict[str, Any], fallback_floor: int | None
) -> int | None:
    floor_reached = _parse_int(raw_payload.get("floor_reached"))
    if floor_reached is not None:
        return floor_reached

    map_points_floor = _count_map_points(raw_payload.get("map_point_history"))
    if map_points_floor > 0:
        return map_points_floor

    return fallback_floor


def _extract_live_card_choice_from_raw_payload(
    raw_payload: dict[str, Any],
) -> tuple[int | None, list[str], str | None]:
    history = raw_payload.get("map_point_history")
    if not isinstance(history, list):
        return None, [], None

    floor = 0
    latest_floor: int | None = None
    latest_offered_cards: list[str] = []
    latest_picked_card: str | None = None

    for act in history:
        if not isinstance(act, list):
            continue
        for map_point in act:
            if not isinstance(map_point, dict):
                continue

            floor += 1
            player_stats = map_point.get("player_stats")
            if not isinstance(player_stats, list):
                continue

            for stats in player_stats:
                if not isinstance(stats, dict):
                    continue

                card_choices = stats.get("card_choices")
                if not isinstance(card_choices, list):
                    continue

                offered_cards: list[str] = []
                picked_card: str | None = None
                for card_choice in card_choices:
                    if not isinstance(card_choice, dict):
                        continue
                    card = card_choice.get("card")
                    if not isinstance(card, dict):
                        continue
                    card_id = card.get("id")
                    if not isinstance(card_id, str) or not card_id:
                        continue

                    offered_cards.append(card_id)
                    if card_choice.get("was_picked") is True:
                        picked_card = card_id

                if not offered_cards:
                    continue

                latest_floor = floor
                latest_offered_cards = offered_cards
                latest_picked_card = picked_card

    return latest_floor, latest_offered_cards, latest_picked_card


def get_live_context(session: Session) -> LiveContextResult:
    run_recency = func.coalesce(
        func.nullif(col(Run.imported_at), ""),
        func.nullif(col(Run.raw_timestamp), ""),
        "1970-01-01T00:00:00Z",
    )
    run = session.exec(
        select(Run).order_by(desc(run_recency), desc(col(Run.id))).limit(1)
    ).first()
    if run is None:
        return LiveContextResult(
            available=False,
            run_id=None,
            character=None,
            ascension=None,
            floor=None,
            offered_cards=[],
            picked_card=None,
        )

    card_choice = session.exec(
        select(CardChoice)
        .where(col(CardChoice.run_id) == run.id)
        .order_by(col(CardChoice.floor).desc(), col(CardChoice.id).desc())
        .limit(1)
    ).first()

    raw_choice_floor, raw_offered_cards, raw_picked_card = (
        _extract_live_card_choice_from_raw_payload(run.raw_payload or {})
    )

    offered_cards = (
        raw_offered_cards
        if raw_offered_cards
        else list(card_choice.offered_cards)
        if card_choice
        else []
    )
    picked_card = (
        raw_picked_card
        if raw_offered_cards
        else card_choice.picked_card
        if card_choice
        else None
    )

    floor = _resolve_live_floor(
        run.raw_payload or {},
        raw_choice_floor
        if raw_choice_floor is not None
        else card_choice.floor
        if card_choice
        else None,
    )

    return LiveContextResult(
        available=True,
        run_id=run.id,
        character=run.character,
        ascension=run.ascension,
        floor=floor,
        offered_cards=offered_cards,
        picked_card=picked_card,
    )
