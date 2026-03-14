from __future__ import annotations

import json

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from core.db.models import CardChoice, Run
from core.ingestion.importer import MAX_RECENT_ISSUES, import_history


def _write_run(path, *, run_id: str, victory: bool, picked: str) -> None:
    payload = {
        "run_id": run_id,
        "character_chosen": "IRONCLAD",
        "ascension_level": 5,
        "seed_played": "SEED",
        "victory": victory,
        "card_choices": [
            {
                "floor": 2,
                "picked": picked,
                "not_picked": ["CARD.A", "CARD.B"],
            }
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_import_history_upserts_existing_run(tmp_path):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    history_dir = tmp_path / "history"
    history_dir.mkdir(parents=True, exist_ok=True)
    run_file = history_dir / "test.run"

    _write_run(run_file, run_id="run-100", victory=False, picked="CARD.BASH")

    with Session(engine) as session:
        first_report = import_history(history_dir, session)
        assert first_report.scanned == 1
        assert first_report.imported == 1
        assert first_report.updated == 0

        run = session.get(Run, "run-100")
        assert run is not None
        assert run.win is False
        assert run.source_file is not None
        assert run.raw_payload["run_id"] == "run-100"
        assert run.source_file.endswith("test.run")
        assert run.imported_at

        _write_run(run_file, run_id="run-100", victory=True, picked="CARD.STRIKE")
        second_report = import_history(history_dir, session)

        assert second_report.scanned == 1
        assert second_report.imported == 0
        assert second_report.updated == 1

        updated_run = session.get(Run, "run-100")
        assert updated_run is not None
        assert updated_run.win is True
        assert updated_run.raw_payload["victory"] is True
        assert updated_run.imported_at

        picks = session.exec(
            select(CardChoice).where(CardChoice.run_id == "run-100")
        ).all()
        assert len(picks) == 1
        assert picks[0].picked_card == "CARD.STRIKE"


def test_import_history_collects_parse_errors_with_diagnostics(tmp_path):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    history_dir = tmp_path / "history"
    history_dir.mkdir(parents=True, exist_ok=True)
    run_file = history_dir / "broken.run"
    run_file.write_text("{broken-json}", encoding="utf-8")

    with Session(engine) as session:
        report = import_history(history_dir, session)

    assert report.scanned == 1
    assert report.parse_errors == 1
    assert report.skipped == 0
    assert len(report.recent_issues) == 1
    issue = report.recent_issues[0]
    assert issue.kind == "parse_error"
    assert issue.file_path.endswith("broken.run")
    assert "invalid json" in issue.message
    assert issue.timestamp


def test_import_history_keeps_only_latest_recent_issues(tmp_path):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    history_dir = tmp_path / "history"
    history_dir.mkdir(parents=True, exist_ok=True)

    for idx in range(MAX_RECENT_ISSUES + 5):
        run_file = history_dir / f"broken-{idx:02}.run"
        run_file.write_text("{broken-json}", encoding="utf-8")

    with Session(engine) as session:
        report = import_history(history_dir, session)

    assert report.scanned == MAX_RECENT_ISSUES + 5
    assert report.parse_errors == MAX_RECENT_ISSUES + 5
    assert len(report.recent_issues) == MAX_RECENT_ISSUES
    assert report.recent_issues[0].file_path.endswith("broken-05.run")
    assert report.recent_issues[-1].file_path.endswith("broken-24.run")
