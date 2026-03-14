from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from typing import Any, cast

from sqlmodel import Session, delete, select

from core.db.models import CardChoice, RelicHistory, Run
from core.ingestion.parser import RunParseError, parse_run_file


MAX_RECENT_ISSUES = 20


@dataclass(frozen=True)
class ImportIssue:
    kind: str
    file_path: str
    message: str
    timestamp: str


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class ImportReport:
    scanned: int = 0
    imported: int = 0
    updated: int = 0
    skipped: int = 0
    parse_errors: int = 0
    recent_issues: list[ImportIssue] = field(default_factory=list)
    last_processed_run_id: str | None = None
    last_processed_file: str | None = None
    last_event_at: str | None = None

    def absorb(self, other: "ImportReport") -> None:
        self.scanned += other.scanned
        self.imported += other.imported
        self.updated += other.updated
        self.skipped += other.skipped
        self.parse_errors += other.parse_errors
        self.recent_issues.extend(other.recent_issues)
        if len(self.recent_issues) > MAX_RECENT_ISSUES:
            self.recent_issues = self.recent_issues[-MAX_RECENT_ISSUES:]
        if other.last_processed_run_id is not None:
            self.last_processed_run_id = other.last_processed_run_id
        if other.last_processed_file is not None:
            self.last_processed_file = other.last_processed_file
        if other.last_event_at is not None:
            self.last_event_at = other.last_event_at


def _upsert_run(session: Session, file_path: Path) -> tuple[str, str]:
    parsed = parse_run_file(file_path)
    imported_at = _utc_now_iso()
    card_choices_table = cast(Any, getattr(CardChoice, "__table__"))
    relic_history_table = cast(Any, getattr(RelicHistory, "__table__"))
    existing = session.get(Run, parsed.run_id)
    if existing:
        existing.seed = parsed.seed
        existing.character = parsed.character
        existing.ascension = parsed.ascension
        existing.win = parsed.win
        existing.raw_timestamp = parsed.raw_timestamp
        existing.imported_at = imported_at
        existing.source_file = str(file_path)
        existing.raw_payload = parsed.raw_payload

        session.exec(
            delete(CardChoice).where(card_choices_table.c.run_id == parsed.run_id)
        )
        session.exec(
            delete(RelicHistory).where(relic_history_table.c.run_id == parsed.run_id)
        )
        status = "updated"
    else:
        session.add(
            Run(
                id=parsed.run_id,
                seed=parsed.seed,
                character=parsed.character,
                ascension=parsed.ascension,
                win=parsed.win,
                raw_timestamp=parsed.raw_timestamp,
                imported_at=imported_at,
                source_file=str(file_path),
                raw_payload=parsed.raw_payload,
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

    return status, parsed.run_id


def import_history(history_path: Path, session: Session) -> ImportReport:
    report = ImportReport()
    if not history_path.exists():
        return report

    for run_file in sorted(history_path.glob("*.run")):
        report.absorb(import_run_file(run_file, session))

    return report


def import_run_file(run_file: Path, session: Session) -> ImportReport:
    report = ImportReport(scanned=1)
    event_time = _utc_now_iso()
    try:
        status, run_id = _upsert_run(session, run_file)
        if status == "updated":
            report.updated += 1
        else:
            report.imported += 1
        report.last_processed_run_id = run_id
        report.last_processed_file = str(run_file)
        report.last_event_at = event_time
        session.commit()
    except RunParseError as exc:
        session.rollback()
        report.parse_errors += 1
        report.last_processed_file = str(run_file)
        report.last_event_at = event_time
        report.recent_issues.append(
            ImportIssue(
                kind="parse_error",
                file_path=str(run_file),
                message=str(exc),
                timestamp=event_time,
            )
        )
    except Exception as exc:
        session.rollback()
        report.skipped += 1
        report.last_processed_file = str(run_file)
        report.last_event_at = event_time
        report.recent_issues.append(
            ImportIssue(
                kind="skipped",
                file_path=str(run_file),
                message=str(exc),
                timestamp=event_time,
            )
        )
    return report


def get_known_run_ids(session: Session) -> set[str]:
    rows = session.exec(select(Run.id)).all()
    return set(rows)
