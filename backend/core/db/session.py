from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine

from core.config import get_settings


settings = get_settings()
engine = create_engine(f"sqlite:///{settings.db_path}", echo=False)


def _ensure_runs_columns() -> None:
    expected_columns = {
        "raw_timestamp": "ALTER TABLE runs ADD COLUMN raw_timestamp TEXT",
        "imported_at": "ALTER TABLE runs ADD COLUMN imported_at TEXT",
        "source_file": "ALTER TABLE runs ADD COLUMN source_file TEXT",
        "raw_payload": "ALTER TABLE runs ADD COLUMN raw_payload JSON",
    }
    with engine.begin() as connection:
        columns_result = connection.execute(text("PRAGMA table_info(runs)"))
        existing = {str(row[1]) for row in columns_result}
        for column_name, statement in expected_columns.items():
            if column_name in existing:
                continue
            connection.execute(text(statement))


def init_db() -> None:
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    SQLModel.metadata.create_all(engine)
    _ensure_runs_columns()


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
