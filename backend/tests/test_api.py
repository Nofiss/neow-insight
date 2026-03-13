from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from api.main import app
from api.state import ingest_status
from core.db import get_session
from core.db.models import CardChoice, Run


@pytest.fixture
def client_and_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    def override_get_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    ingest_status.scanned = 0
    ingest_status.imported = 0
    ingest_status.updated = 0
    ingest_status.parse_errors = 0
    ingest_status.skipped = 0
    try:
        with TestClient(app) as client:
            yield client, engine
    finally:
        app.dependency_overrides.clear()
        ingest_status.scanned = 0
        ingest_status.imported = 0
        ingest_status.updated = 0
        ingest_status.parse_errors = 0
        ingest_status.skipped = 0


def test_health_endpoint(client_and_engine):
    client, _ = client_and_engine
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["version"] == "0.1.0"
    assert isinstance(payload["watcher_enabled"], bool)


def test_runs_stats_endpoint(client_and_engine):
    client, engine = client_and_engine
    with Session(engine) as session:
        session.add(Run(id="run-a", win=True, character="IRONCLAD", ascension=10))
        session.add(Run(id="run-b", win=False, character="IRONCLAD", ascension=10))
        session.commit()

    response = client.get("/runs/stats")

    assert response.status_code == 200
    payload = response.json()
    assert payload == {"total_runs": 2, "wins": 1, "win_rate": 0.5}


def test_recommendation_endpoint_selects_best_pick(client_and_engine):
    client, engine = client_and_engine
    with Session(engine) as session:
        session.add_all(
            [
                Run(id="run-1", win=True),
                Run(id="run-2", win=False),
                Run(id="run-3", win=True),
            ]
        )
        session.add_all(
            [
                CardChoice(
                    run_id="run-1",
                    floor=1,
                    offered_cards=["CARD.BASH", "CARD.CLOTHESLINE"],
                    picked_card="CARD.BASH",
                    is_shop=False,
                ),
                CardChoice(
                    run_id="run-2",
                    floor=1,
                    offered_cards=["CARD.BASH", "CARD.CLOTHESLINE"],
                    picked_card="CARD.BASH",
                    is_shop=False,
                ),
                CardChoice(
                    run_id="run-3",
                    floor=1,
                    offered_cards=["CARD.BASH", "CARD.CLOTHESLINE"],
                    picked_card="CARD.CLOTHESLINE",
                    is_shop=False,
                ),
            ]
        )
        session.commit()

    response = client.get("/recommendation?cards=CARD.BASH,CARD.CLOTHESLINE")

    assert response.status_code == 200
    payload = response.json()
    assert payload["best_pick"] == "CARD.CLOTHESLINE"
    assert payload["win_rate_boost"] > 0
    assert payload["confidence"] > 0
    assert payload["sample_size"] == 1
    assert payload["reason"] == "low_sample"
    assert payload["card_win_rate"] == 1.0
    assert payload["global_win_rate"] == 0.6667


def test_recommendation_endpoint_no_history_reason(client_and_engine):
    client, _ = client_and_engine

    response = client.get("/recommendation?cards=CARD.BASH,CARD.CLOTHESLINE")

    assert response.status_code == 200
    payload = response.json()
    assert payload["best_pick"] == "CARD.BASH"
    assert payload["reason"] == "no_history"
    assert payload["sample_size"] == 0
    assert payload["confidence"] == 0.0


def test_ingest_status_endpoint_defaults_to_zero(client_and_engine):
    client, _ = client_and_engine
    response = client.get("/ingest/status")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload.keys()) == {
        "scanned",
        "imported",
        "updated",
        "parse_errors",
        "skipped",
    }
    for key, value in payload.items():
        assert isinstance(value, int)
        assert value >= 0


def test_card_insights_endpoint_returns_expected_rows(client_and_engine):
    client, engine = client_and_engine
    with Session(engine) as session:
        session.add_all(
            [
                Run(id="run-1", win=True),
                Run(id="run-2", win=False),
                Run(id="run-3", win=True),
            ]
        )
        session.add_all(
            [
                CardChoice(
                    run_id="run-1",
                    floor=1,
                    offered_cards=["CARD.BASH", "CARD.CLOTHESLINE"],
                    picked_card="CARD.BASH",
                    is_shop=False,
                ),
                CardChoice(
                    run_id="run-2",
                    floor=1,
                    offered_cards=["CARD.BASH", "CARD.CLOTHESLINE"],
                    picked_card="CARD.BASH",
                    is_shop=False,
                ),
                CardChoice(
                    run_id="run-3",
                    floor=1,
                    offered_cards=["CARD.BASH", "CARD.CLOTHESLINE"],
                    picked_card="CARD.CLOTHESLINE",
                    is_shop=False,
                ),
            ]
        )
        session.commit()

    response = client.get("/runs/card-insights?cards=CARD.BASH,CARD.CLOTHESLINE")

    assert response.status_code == 200
    payload = response.json()
    assert payload["global_win_rate"] == 0.6667
    assert len(payload["insights"]) == 2
    assert payload["insights"][0] == {
        "card": "CARD.BASH",
        "sample_size": 2,
        "card_win_rate": 0.5,
        "win_rate_boost": -0.1667,
    }
    assert payload["insights"][1] == {
        "card": "CARD.CLOTHESLINE",
        "sample_size": 1,
        "card_win_rate": 1.0,
        "win_rate_boost": 0.3333,
    }
