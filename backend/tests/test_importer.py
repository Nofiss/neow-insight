from __future__ import annotations

import json

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from core.db.models import CardChoice, Run
from core.ingestion.importer import import_history


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

        _write_run(run_file, run_id="run-100", victory=True, picked="CARD.STRIKE")
        second_report = import_history(history_dir, session)

        assert second_report.scanned == 1
        assert second_report.imported == 0
        assert second_report.updated == 1

        updated_run = session.get(Run, "run-100")
        assert updated_run is not None
        assert updated_run.win is True

        picks = session.exec(
            select(CardChoice).where(CardChoice.run_id == "run-100")
        ).all()
        assert len(picks) == 1
        assert picks[0].picked_card == "CARD.STRIKE"
