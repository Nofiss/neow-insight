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
    scope: str
    applied_filters: list[str]
    fallback_used: bool


@dataclass(frozen=True)
class RecommendationContext:
    character: str | None = None
    ascension: int | None = None
    floor: int | None = None


@dataclass(frozen=True)
class ScopeConfig:
    scope: str
    applied_filters: list[str]
    context: RecommendationContext


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
    session: Session,
    cards: list[str],
    context: RecommendationContext,
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
    if context.character:
        query = query.where(runs_table.c.character == context.character)
    if context.ascension is not None:
        query = query.where(runs_table.c.ascension == context.ascension)
    if context.floor is not None:
        query = query.where(card_choices_table.c.floor == context.floor)

    rows = session.exec(query).all()
    return {
        str(card): (int(picked_count or 0), int(winning_count or 0))
        for card, picked_count, winning_count in rows
    }


def _normalize_cards(cards: list[str]) -> list[str]:
    return list(dict.fromkeys(card.strip() for card in cards if card and card.strip()))


def _normalize_context(context: RecommendationContext | None) -> RecommendationContext:
    if context is None:
        return RecommendationContext()

    character = context.character.strip() if context.character else None
    if character:
        character = character.upper()

    ascension = (
        context.ascension
        if context.ascension is not None and context.ascension >= 0
        else None
    )
    floor = context.floor if context.floor is not None and context.floor >= 0 else None
    return RecommendationContext(
        character=character or None, ascension=ascension, floor=floor
    )


def _build_scope_chain(context: RecommendationContext) -> list[ScopeConfig]:
    base_scopes: list[ScopeConfig] = []

    if (
        context.character
        and context.ascension is not None
        and context.floor is not None
    ):
        base_scopes.append(
            ScopeConfig(
                scope="character_ascension_floor",
                applied_filters=["character", "ascension", "floor"],
                context=context,
            )
        )
        base_scopes.append(
            ScopeConfig(
                scope="character_ascension",
                applied_filters=["character", "ascension"],
                context=RecommendationContext(
                    character=context.character,
                    ascension=context.ascension,
                    floor=None,
                ),
            )
        )
    elif context.character and context.ascension is not None:
        base_scopes.append(
            ScopeConfig(
                scope="character_ascension",
                applied_filters=["character", "ascension"],
                context=RecommendationContext(
                    character=context.character,
                    ascension=context.ascension,
                    floor=None,
                ),
            )
        )
    elif context.character:
        base_scopes.append(
            ScopeConfig(
                scope="character",
                applied_filters=["character"],
                context=RecommendationContext(character=context.character),
            )
        )
    elif context.ascension is not None:
        base_scopes.append(
            ScopeConfig(
                scope="ascension",
                applied_filters=["ascension"],
                context=RecommendationContext(ascension=context.ascension),
            )
        )

    base_scopes.append(
        ScopeConfig(
            scope="global",
            applied_filters=[],
            context=RecommendationContext(),
        )
    )
    return base_scopes


def _pick_best_card(
    candidates: list[str],
    pick_stats: dict[str, tuple[int, int]],
    global_win_rate: float,
) -> tuple[str, float, int]:
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

    return best_card or candidates[0], best_card_win_rate, best_sample_size


def recommend_card(
    session: Session,
    offered_cards: list[str],
    context: RecommendationContext | None = None,
) -> RecommendationResult:
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
            scope="global",
            applied_filters=[],
            fallback_used=False,
        )

    normalized_context = _normalize_context(context)
    scope_chain = _build_scope_chain(normalized_context)
    context_requested = len(scope_chain) > 1

    total_runs, _, global_win_rate = compute_runs_stats(session)
    if total_runs == 0:
        return RecommendationResult(
            best_pick=candidates[0],
            win_rate_boost=0.0,
            confidence=0.0,
            sample_size=0,
            card_win_rate=0.0,
            global_win_rate=0.0,
            reason="no_history_global",
            scope="global",
            applied_filters=[],
            fallback_used=False,
        )

    selected_scope = scope_chain[-1]
    selected_stats: dict[str, tuple[int, int]] = _compute_card_pick_stats(
        session,
        candidates,
        selected_scope.context,
    )
    fallback_used = False
    missing_primary_context = False

    for index, scope in enumerate(scope_chain):
        scoped_stats = _compute_card_pick_stats(session, candidates, scope.context)
        has_scoped_history = any(
            picked_count > 0 for picked_count, _ in scoped_stats.values()
        )
        if has_scoped_history:
            selected_scope = scope
            selected_stats = scoped_stats
            fallback_used = index > 0
            break
        if index == 0 and scope.scope != "global":
            missing_primary_context = True

    best_card, best_card_win_rate, best_sample_size = _pick_best_card(
        candidates,
        selected_stats,
        global_win_rate,
    )

    boost = best_card_win_rate - global_win_rate
    confidence = min(best_sample_size / CONFIDENCE_SCALE, 1.0)
    if selected_scope.scope == "global":
        if context_requested and fallback_used and missing_primary_context:
            reason = "fallback_global_no_context"
        else:
            reason = (
                "low_sample_global"
                if best_sample_size < LOW_SAMPLE_THRESHOLD
                else "ok_global"
            )
    else:
        reason = (
            "low_sample_contextual"
            if best_sample_size < LOW_SAMPLE_THRESHOLD
            else "ok_contextual"
        )

    return RecommendationResult(
        best_pick=best_card,
        win_rate_boost=round(boost, 4),
        confidence=round(confidence, 4),
        sample_size=best_sample_size,
        card_win_rate=round(best_card_win_rate, 4),
        global_win_rate=round(global_win_rate, 4),
        reason=reason,
        scope=selected_scope.scope,
        applied_filters=selected_scope.applied_filters,
        fallback_used=fallback_used,
    )


def compute_card_insights(
    session: Session, offered_cards: list[str]
) -> tuple[float, list[CardInsightResult]]:
    candidates = _normalize_cards(offered_cards)
    if not candidates:
        return 0.0, []

    _, _, global_win_rate = compute_runs_stats(session)
    pick_stats = _compute_card_pick_stats(session, candidates, RecommendationContext())

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
