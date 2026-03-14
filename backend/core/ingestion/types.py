from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ParsedCardChoice:
    floor: int
    offered_cards: list[str]
    picked_card: str
    is_shop: bool = False


@dataclass(frozen=True)
class ParsedRelic:
    relic_id: str
    floor: int


@dataclass(frozen=True)
class ParsedRun:
    run_id: str
    seed: str | None
    character: str | None
    ascension: int | None
    win: bool
    raw_timestamp: str | None
    raw_payload: dict[str, Any]
    card_choices: list[ParsedCardChoice] = field(default_factory=list)
    relic_history: list[ParsedRelic] = field(default_factory=list)
