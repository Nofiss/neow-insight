from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from core.ingestion.types import ParsedCardChoice, ParsedRelic, ParsedRun


class RunParseError(Exception):
    pass


def _parse_int(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def _normalize_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    normalized: list[str] = []
    for item in values:
        if isinstance(item, str) and item:
            normalized.append(item)
    return normalized


def _parse_relic_history(values: Any) -> list[ParsedRelic]:
    relic_history: list[ParsedRelic] = []
    if not isinstance(values, list):
        return relic_history

    for idx, item in enumerate(values, start=1):
        if isinstance(item, str):
            relic_history.append(ParsedRelic(relic_id=item, floor=idx))
            continue
        if isinstance(item, dict):
            relic_id = item.get("key")
            floor = _parse_int(item.get("floor"))
            if isinstance(relic_id, str) and relic_id:
                relic_history.append(ParsedRelic(relic_id=relic_id, floor=floor or idx))
    return relic_history


def _parse_run_timestamp(payload: dict[str, Any]) -> str | None:
    timestamp_fields = [
        "start_time",
        "run_time",
        "timestamp",
        "local_time",
        "run_timestamp",
        "playtime_timestamp",
        "playtime",
    ]
    for field_name in timestamp_fields:
        value = payload.get(field_name)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, int | float):
            return str(value)
    return None


def _parse_seed(payload: dict[str, Any]) -> str | None:
    for field_name in ("seed_played", "seed"):
        value = payload.get(field_name)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, int | float):
            return str(value)
    return None


def _parse_character(payload: dict[str, Any]) -> str | None:
    legacy_character = payload.get("character_chosen")
    if isinstance(legacy_character, str) and legacy_character.strip():
        return legacy_character.strip()

    players = payload.get("players")
    if not isinstance(players, list):
        return None
    if not players:
        return None
    first_player = players[0]
    if not isinstance(first_player, dict):
        return None
    character = first_player.get("character")
    if isinstance(character, str) and character.strip():
        return character.strip()

    character_id = first_player.get("character_id")
    if isinstance(character_id, str) and character_id.strip():
        return character_id.strip()
    return None


def _flatten_map_points(payload: dict[str, Any]) -> list[tuple[int, dict[str, Any]]]:
    points: list[tuple[int, dict[str, Any]]] = []
    history = payload.get("map_point_history")
    if not isinstance(history, list):
        return points

    floor = 0
    for act in history:
        if not isinstance(act, list):
            continue
        for map_point in act:
            if not isinstance(map_point, dict):
                continue
            floor += 1
            points.append((floor, map_point))
    return points


def _parse_card_choices_sts2(payload: dict[str, Any]) -> list[ParsedCardChoice]:
    parsed_choices: list[ParsedCardChoice] = []
    for floor, map_point in _flatten_map_points(payload):
        map_point_type = map_point.get("map_point_type")
        is_shop = isinstance(map_point_type, str) and map_point_type == "shop"
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

            if picked_card is None:
                continue
            parsed_choices.append(
                ParsedCardChoice(
                    floor=floor,
                    offered_cards=offered_cards,
                    picked_card=picked_card,
                    is_shop=is_shop,
                )
            )
    return parsed_choices


def _parse_relic_history_sts2(payload: dict[str, Any]) -> list[ParsedRelic]:
    relics: list[ParsedRelic] = []

    players = payload.get("players")
    if isinstance(players, list) and players:
        first_player = players[0]
        if isinstance(first_player, dict):
            starting_relics = first_player.get("relics")
            if isinstance(starting_relics, list):
                for relic in starting_relics:
                    if isinstance(relic, str) and relic:
                        relics.append(ParsedRelic(relic_id=relic, floor=1))

    for floor, map_point in _flatten_map_points(payload):
        player_stats = map_point.get("player_stats")
        if not isinstance(player_stats, list):
            continue

        for stats in player_stats:
            if not isinstance(stats, dict):
                continue
            relic_choices = stats.get("relic_choices")
            if not isinstance(relic_choices, list):
                continue

            for relic_choice in relic_choices:
                if not isinstance(relic_choice, dict):
                    continue
                relic_id = relic_choice.get("choice")
                if not isinstance(relic_id, str) or not relic_id:
                    continue
                if relic_choice.get("was_picked") is True:
                    relics.append(ParsedRelic(relic_id=relic_id, floor=floor))

    deduped: list[ParsedRelic] = []
    seen: set[tuple[str, int]] = set()
    for relic in relics:
        key = (relic.relic_id, relic.floor)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(relic)
    return deduped


def parse_run_file(path: Path) -> ParsedRun:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RunParseError(f"cannot read file: {path}") from exc

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RunParseError(f"invalid json in file: {path}") from exc

    if not isinstance(payload, dict):
        raise RunParseError("run payload must be an object")

    run_id = payload.get("run_id")
    if not isinstance(run_id, str) or not run_id.strip():
        digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()
        run_id = f"generated-{digest}"

    character = _parse_character(payload)

    ascension = _parse_int(payload.get("ascension_level"))
    if ascension is None:
        ascension = _parse_int(payload.get("ascension"))

    seed = _parse_seed(payload)

    if "victory" in payload:
        win = bool(payload.get("victory", False))
    else:
        win = bool(payload.get("win", False))

    card_choices_payload = payload.get("card_choices", [])
    card_choices: list[ParsedCardChoice] = []
    if isinstance(card_choices_payload, list):
        for choice in card_choices_payload:
            if not isinstance(choice, dict):
                continue
            floor = _parse_int(choice.get("floor"))
            picked = choice.get("picked")
            if floor is None or not isinstance(picked, str) or not picked:
                continue
            card_choices.append(
                ParsedCardChoice(
                    floor=floor,
                    offered_cards=_normalize_list(choice.get("not_picked")),
                    picked_card=picked,
                    is_shop=bool(choice.get("is_shop", False)),
                )
            )

    relic_history = _parse_relic_history(payload.get("relics_obtained", []))
    if not card_choices:
        card_choices = _parse_card_choices_sts2(payload)
    if not relic_history:
        relic_history = _parse_relic_history_sts2(payload)
    raw_timestamp = _parse_run_timestamp(payload)

    return ParsedRun(
        run_id=run_id,
        seed=seed,
        character=character,
        ascension=ascension,
        win=win,
        raw_timestamp=raw_timestamp,
        raw_payload=payload,
        card_choices=card_choices,
        relic_history=relic_history,
    )
