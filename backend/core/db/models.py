from __future__ import annotations

from typing import Optional

from sqlalchemy import JSON, Column, Index
from sqlmodel import Field, SQLModel


class Run(SQLModel, table=True):
    __tablename__ = "runs"

    id: str = Field(primary_key=True)
    seed: Optional[str] = Field(default=None, index=True)
    character: Optional[str] = Field(default=None, index=True)
    ascension: Optional[int] = Field(default=None, index=True)
    win: bool = Field(default=False, index=True)


class CardChoice(SQLModel, table=True):
    __tablename__ = "card_choices"

    id: Optional[int] = Field(default=None, primary_key=True)
    run_id: str = Field(foreign_key="runs.id")
    floor: int = Field(index=True)
    offered_cards: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    picked_card: str = Field(index=True)
    is_shop: bool = Field(default=False)


class RelicHistory(SQLModel, table=True):
    __tablename__ = "relic_history"

    id: Optional[int] = Field(default=None, primary_key=True)
    run_id: str = Field(foreign_key="runs.id")
    relic_id: str = Field(index=True)
    floor: int = Field(index=True)


Index("ix_card_choices_run_floor", CardChoice.run_id, CardChoice.floor)
Index("ix_relic_history_run_floor", RelicHistory.run_id, RelicHistory.floor)
