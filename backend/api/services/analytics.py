from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

from sqlalchemy import case
from sqlmodel import Session, func, select

from core.db.models import CardChoice, Run


LOW_SAMPLE_THRESHOLD = 5
CONFIDENCE_SCALE = 20.0
SMOOTHING_FACTOR = 8.0


@dataclass
class RecommendationResult:
    best_pick: str | None
    win_rate_boost: float
    confidence: float
    sample_size: int
    card_win_rate: float
    global_win_rate: float
    reason: str


@dataclass
class CardInsightResult:
    card: str
    sample_size: int
    card_win_rate: float
    win_rate_boost: float


def compute_runs_stats(session: Session) -> tuple[int, int, float]:
    runs_table = cast(Any, getattr(Run, "__table__"))
    total_runs = session.exec(select(func.count(runs_table.c.id))).one() or 0
    wins = (
        session.exec(
            select(func.count(runs_table.c.id)).where(runs_table.c.win.is_(True))
        ).one()
        or 0
    )
    win_rate = float(wins / total_runs) if total_runs else 0.0
    return int(total_runs), int(wins), round(win_rate, 4)


def _compute_card_pick_stats(
    session: Session, cards: list[str]
) -> dict[str, tuple[int, int]]:
    if not cards:
        return {}

    runs_table = cast(Any, getattr(Run, "__table__"))
    card_choices_table = cast(Any, getattr(CardChoice, "__table__"))

    query = (
        select(
            card_choices_table.c.picked_card,
            func.count(card_choices_table.c.id),
            func.sum(case((runs_table.c.win.is_(True), 1), else_=0)),
        )
        .select_from(card_choices_table)
        .join(runs_table, runs_table.c.id == card_choices_table.c.run_id)
        .where(card_choices_table.c.picked_card.in_(cards))
        .group_by(card_choices_table.c.picked_card)
    )
    rows = session.exec(query).all()
    return {
        str(card): (int(picked_count or 0), int(winning_count or 0))
        for card, picked_count, winning_count in rows
    }


def _normalize_cards(cards: list[str]) -> list[str]:
    return list(dict.fromkeys(card.strip() for card in cards if card and card.strip()))


def recommend_card(session: Session, offered_cards: list[str]) -> RecommendationResult:
    candidates = _normalize_cards(offered_cards)
    if not candidates:
        return RecommendationResult(
            best_pick=None,
            win_rate_boost=0.0,
            confidence=0.0,
            sample_size=0,
            card_win_rate=0.0,
            global_win_rate=0.0,
            reason="no_candidates",
        )

    total_runs, _, global_win_rate = compute_runs_stats(session)
    if total_runs == 0:
        return RecommendationResult(
            best_pick=candidates[0],
            win_rate_boost=0.0,
            confidence=0.0,
            sample_size=0,
            card_win_rate=0.0,
            global_win_rate=0.0,
            reason="no_history",
        )

    pick_stats = _compute_card_pick_stats(session, candidates)

    best_card: str | None = None
    best_score = -1.0
    best_card_win_rate = 0.0
    best_sample_size = 0

    for card in candidates:
        picked_count, winning_count = pick_stats.get(card, (0, 0))
        if not picked_count:
            score = global_win_rate
            card_win_rate = global_win_rate
        else:
            card_win_rate = float(winning_count / picked_count)
            smoothed_win_rate = (winning_count + global_win_rate * SMOOTHING_FACTOR) / (
                picked_count + SMOOTHING_FACTOR
            )
            score = smoothed_win_rate * (1 + min(float(picked_count) / 100, 1.0))

        if score > best_score:
            best_score = score
            best_card = card
            best_card_win_rate = card_win_rate
            best_sample_size = picked_count

    boost = best_card_win_rate - global_win_rate
    confidence = min(best_sample_size / CONFIDENCE_SCALE, 1.0)
    reason = "low_sample" if best_sample_size < LOW_SAMPLE_THRESHOLD else "ok"

    return RecommendationResult(
        best_pick=best_card,
        win_rate_boost=round(boost, 4),
        confidence=round(confidence, 4),
        sample_size=best_sample_size,
        card_win_rate=round(best_card_win_rate, 4),
        global_win_rate=round(global_win_rate, 4),
        reason=reason,
    )


def compute_card_insights(
    session: Session, offered_cards: list[str]
) -> tuple[float, list[CardInsightResult]]:
    candidates = _normalize_cards(offered_cards)
    if not candidates:
        return 0.0, []

    _, _, global_win_rate = compute_runs_stats(session)
    pick_stats = _compute_card_pick_stats(session, candidates)

    insights: list[CardInsightResult] = []
    for card in candidates:
        picked_count, winning_count = pick_stats.get(card, (0, 0))
        if picked_count:
            card_win_rate = float(winning_count / picked_count)
        else:
            card_win_rate = global_win_rate

        insights.append(
            CardInsightResult(
                card=card,
                sample_size=picked_count,
                card_win_rate=round(card_win_rate, 4),
                win_rate_boost=round(card_win_rate - global_win_rate, 4),
            )
        )

    return round(global_win_rate, 4), insights
