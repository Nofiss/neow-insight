from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlmodel import Session, delete, select

from core.db.models import CardChoice, RelicHistory, Run
from core.ingestion.parser import RunParseError, parse_run_file


@dataclass
class ImportReport:
    scanned: int = 0
    imported: int = 0
    updated: int = 0
    skipped: int = 0
    parse_errors: int = 0

    def absorb(self, other: "ImportReport") -> None:
        self.scanned += other.scanned
        self.imported += other.imported
        self.updated += other.updated
        self.skipped += other.skipped
        self.parse_errors += other.parse_errors


def _upsert_run(session: Session, file_path: Path) -> str:
    parsed = parse_run_file(file_path)
    existing = session.get(Run, parsed.run_id)
    if existing:
        existing.seed = parsed.seed
        existing.character = parsed.character
        existing.ascension = parsed.ascension
        existing.win = parsed.win

        session.exec(delete(CardChoice).where(CardChoice.run_id == parsed.run_id))
        session.exec(delete(RelicHistory).where(RelicHistory.run_id == parsed.run_id))
        status = "updated"
    else:
        session.add(
            Run(
                id=parsed.run_id,
                seed=parsed.seed,
                character=parsed.character,
                ascension=parsed.ascension,
                win=parsed.win,
            )
        )
        status = "imported"

    for choice in parsed.card_choices:
        offered_cards = list(choice.offered_cards)
        if choice.picked_card not in offered_cards:
            offered_cards.append(choice.picked_card)
        session.add(
            CardChoice(
                run_id=parsed.run_id,
                floor=choice.floor,
                offered_cards=offered_cards,
                picked_card=choice.picked_card,
                is_shop=choice.is_shop,
            )
        )

    for relic in parsed.relic_history:
        session.add(
            RelicHistory(
                run_id=parsed.run_id, relic_id=relic.relic_id, floor=relic.floor
            )
        )

    return status


def import_history(history_path: Path, session: Session) -> ImportReport:
    report = ImportReport()
    if not history_path.exists():
        return report

    for run_file in sorted(history_path.glob("*.run")):
        report.absorb(import_run_file(run_file, session))

    return report


def import_run_file(run_file: Path, session: Session) -> ImportReport:
    report = ImportReport(scanned=1)
    try:
        status = _upsert_run(session, run_file)
        if status == "updated":
            report.updated += 1
        else:
            report.imported += 1
        session.commit()
    except RunParseError:
        session.rollback()
        report.parse_errors += 1
    except Exception:
        session.rollback()
        report.skipped += 1
    return report


def get_known_run_ids(session: Session) -> set[str]:
    rows = session.exec(select(Run.id)).all()
    return set(rows)
