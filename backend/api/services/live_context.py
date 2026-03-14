from __future__ import annotations

from dataclasses import dataclass

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


def get_live_context(session: Session) -> LiveContextResult:
    run_recency = func.coalesce(
        func.nullif(col(Run.imported_at), ""),
        func.nullif(col(Run.raw_timestamp), ""),
        "1970-01-01T00:00:00Z",
    )
    run_ids_with_choices = select(col(CardChoice.run_id)).distinct()
    run = session.exec(
        select(Run)
        .where(col(Run.id).in_(run_ids_with_choices))
        .order_by(desc(run_recency), desc(col(Run.id)))
        .limit(1)
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
    if card_choice is None:
        return LiveContextResult(
            available=False,
            run_id=None,
            character=None,
            ascension=None,
            floor=None,
            offered_cards=[],
            picked_card=None,
        )

    return LiveContextResult(
        available=True,
        run_id=run.id,
        character=run.character,
        ascension=run.ascension,
        floor=card_choice.floor,
        offered_cards=list(card_choice.offered_cards),
        picked_card=card_choice.picked_card,
    )
