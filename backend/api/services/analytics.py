from __future__ import annotations

from sqlalchemy import case
from sqlmodel import Session, func, select

from core.db.models import CardChoice, Run


def compute_runs_stats(session: Session) -> tuple[int, int, float]:
    total_runs = session.exec(select(func.count(Run.id))).one() or 0
    wins = session.exec(select(func.count(Run.id)).where(Run.win.is_(True))).one() or 0
    win_rate = float(wins / total_runs) if total_runs else 0.0
    return int(total_runs), int(wins), round(win_rate, 4)


def recommend_card(
    session: Session, offered_cards: list[str]
) -> tuple[str | None, float, float]:
    candidates = [card for card in offered_cards if card]
    if not candidates:
        return None, 0.0, 0.0

    total_runs, wins, global_win_rate = compute_runs_stats(session)
    if total_runs == 0:
        return candidates[0], 0.0, 0.0

    best_card: str | None = None
    best_score = -1.0
    best_card_win_rate = 0.0
    sample_count = 0

    for card in candidates:
        picks_query = (
            select(
                func.count(CardChoice.id),
                func.sum(case((Run.win.is_(True), 1), else_=0)),
            )
            .join(Run, Run.id == CardChoice.run_id)
            .where(CardChoice.picked_card == card)
        )
        picked_count, winning_count = session.exec(picks_query).one()
        if not picked_count:
            score = 0.0
            card_win_rate = global_win_rate
        else:
            card_win_rate = float(winning_count / picked_count)
            score = card_win_rate * (1 + min(float(picked_count) / 100, 1.0))

        if score > best_score:
            best_score = score
            best_card = card
            best_card_win_rate = card_win_rate
            sample_count = int(picked_count or 0)

    boost = best_card_win_rate - global_win_rate
    confidence = min(sample_count / 20.0, 1.0)
    return best_card, round(boost, 4), round(confidence, 4)
