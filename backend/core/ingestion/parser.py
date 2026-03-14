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

    character = payload.get("character_chosen")
    if not isinstance(character, str):
        character = None

    ascension = _parse_int(payload.get("ascension_level"))
    seed = payload.get("seed_played")
    if not isinstance(seed, str):
        seed = None

    win = bool(payload.get("victory", False))

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
