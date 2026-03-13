from __future__ import annotations

from dataclasses import dataclass

from sqlmodel import Session, select

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
    row = session.exec(
        select(CardChoice, Run)
        .join(Run, Run.id == CardChoice.run_id)
        .order_by(CardChoice.id.desc())
        .limit(1)
    ).first()
    if row is None:
        return LiveContextResult(
            available=False,
            run_id=None,
            character=None,
            ascension=None,
            floor=None,
            offered_cards=[],
            picked_card=None,
        )

    card_choice, run = row
    return LiveContextResult(
        available=True,
        run_id=run.id,
        character=run.character,
        ascension=run.ascension,
        floor=card_choice.floor,
        offered_cards=list(card_choice.offered_cards),
        picked_card=card_choice.picked_card,
    )
