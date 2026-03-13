from __future__ import annotations

from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from core.config import get_settings


settings = get_settings()
engine = create_engine(f"sqlite:///{settings.db_path}", echo=False)


def init_db() -> None:
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
