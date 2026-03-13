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
    ingest_status.recent_issues = []
    ingest_status.last_processed_run_id = None
    ingest_status.last_processed_file = None
    ingest_status.last_event_at = None
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
        ingest_status.recent_issues = []
        ingest_status.last_processed_run_id = None
        ingest_status.last_processed_file = None
        ingest_status.last_event_at = None


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
    assert payload["reason"] == "low_sample_global"
    assert payload["card_win_rate"] == 1.0
    assert payload["global_win_rate"] == 0.6667
    assert payload["scope"] == "global"
    assert payload["applied_filters"] == []
    assert payload["fallback_used"] is False


def test_recommendation_endpoint_no_history_reason(client_and_engine):
    client, _ = client_and_engine

    response = client.get("/recommendation?cards=CARD.BASH,CARD.CLOTHESLINE")

    assert response.status_code == 200
    payload = response.json()
    assert payload["best_pick"] == "CARD.BASH"
    assert payload["reason"] == "no_history_global"
    assert payload["sample_size"] == 0
    assert payload["confidence"] == 0.0
    assert payload["scope"] == "global"
    assert payload["applied_filters"] == []
    assert payload["fallback_used"] is False


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
        "recent_issues",
        "last_processed_run_id",
        "last_processed_file",
        "last_event_at",
    }
    for key, value in payload.items():
        if key in {
            "recent_issues",
            "last_processed_run_id",
            "last_processed_file",
            "last_event_at",
        }:
            continue
        assert isinstance(value, int)
        assert value >= 0
    assert payload["recent_issues"] == []
    assert payload["last_processed_run_id"] is None
    assert payload["last_processed_file"] is None
    assert payload["last_event_at"] is None


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


def test_card_insights_endpoint_empty_cards_query_returns_empty_insights(
    client_and_engine,
):
    client, _ = client_and_engine

    response = client.get("/runs/card-insights?cards=")

    assert response.status_code == 200
    payload = response.json()
    assert payload["global_win_rate"] == 0.0
    assert payload["insights"] == []


def test_card_insights_endpoint_without_cards_param_returns_empty_insights(
    client_and_engine,
):
    client, _ = client_and_engine

    response = client.get("/runs/card-insights")

    assert response.status_code == 200
    payload = response.json()
    assert payload["global_win_rate"] == 0.0
    assert payload["insights"] == []


def test_card_insights_endpoint_trims_and_deduplicates_cards(client_and_engine):
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

    response = client.get(
        "/runs/card-insights?cards=  CARD.BASH , CARD.BASH  ,  CARD.CLOTHESLINE  "
    )

    assert response.status_code == 200
    payload = response.json()
    assert [item["card"] for item in payload["insights"]] == [
        "CARD.BASH",
        "CARD.CLOTHESLINE",
    ]


def test_card_insights_endpoint_unknown_card_uses_global_win_rate(client_and_engine):
    client, engine = client_and_engine
    with Session(engine) as session:
        session.add_all(
            [
                Run(id="run-1", win=True),
                Run(id="run-2", win=False),
                Run(id="run-3", win=True),
            ]
        )
        session.commit()

    response = client.get("/runs/card-insights?cards=CARD.UNKNOWN")

    assert response.status_code == 200
    payload = response.json()
    assert payload["global_win_rate"] == 0.6667
    assert payload["insights"] == [
        {
            "card": "CARD.UNKNOWN",
            "sample_size": 0,
            "card_win_rate": 0.6667,
            "win_rate_boost": 0.0,
        }
    ]


def test_card_insights_endpoint_handles_long_card_list(client_and_engine):
    client, _ = client_and_engine
    cards = [f"CARD.TEST_{index}" for index in range(1, 51)]
    query = ",".join(cards)

    response = client.get(f"/runs/card-insights?cards={query}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["global_win_rate"] == 0.0
    assert len(payload["insights"]) == 50
    assert [item["card"] for item in payload["insights"]] == cards


def test_recommendation_endpoint_trims_and_deduplicates_cards(client_and_engine):
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

    response = client.get(
        "/recommendation?cards=  CARD.BASH , CARD.BASH  ,  CARD.CLOTHESLINE  "
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["best_pick"] == "CARD.CLOTHESLINE"
    assert payload["sample_size"] == 1
    assert payload["reason"] == "low_sample_global"


def test_recommendation_endpoint_prefers_contextual_scope_when_history_exists(
    client_and_engine,
):
    client, engine = client_and_engine
    with Session(engine) as session:
        session.add_all(
            [
                Run(id="run-a", win=True, character="IRONCLAD", ascension=10),
                Run(id="run-b", win=False, character="IRONCLAD", ascension=10),
                Run(id="run-c", win=False, character="IRONCLAD", ascension=10),
                Run(id="run-d", win=True, character="SILENT", ascension=10),
                Run(id="run-e", win=False, character="SILENT", ascension=10),
            ]
        )
        session.add_all(
            [
                CardChoice(
                    run_id="run-a",
                    floor=2,
                    offered_cards=["CARD.BASH", "CARD.CLOTHESLINE"],
                    picked_card="CARD.BASH",
                    is_shop=False,
                ),
                CardChoice(
                    run_id="run-b",
                    floor=2,
                    offered_cards=["CARD.BASH", "CARD.CLOTHESLINE"],
                    picked_card="CARD.BASH",
                    is_shop=False,
                ),
                CardChoice(
                    run_id="run-c",
                    floor=2,
                    offered_cards=["CARD.BASH", "CARD.CLOTHESLINE"],
                    picked_card="CARD.CLOTHESLINE",
                    is_shop=False,
                ),
                CardChoice(
                    run_id="run-d",
                    floor=2,
                    offered_cards=["CARD.BASH", "CARD.CLOTHESLINE"],
                    picked_card="CARD.CLOTHESLINE",
                    is_shop=False,
                ),
                CardChoice(
                    run_id="run-e",
                    floor=2,
                    offered_cards=["CARD.BASH", "CARD.CLOTHESLINE"],
                    picked_card="CARD.CLOTHESLINE",
                    is_shop=False,
                ),
            ]
        )
        session.commit()

    response = client.get(
        "/recommendation?cards=CARD.BASH,CARD.CLOTHESLINE&character=IRONCLAD&ascension=10&floor=2"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["best_pick"] == "CARD.BASH"
    assert payload["scope"] == "character_ascension_floor"
    assert payload["applied_filters"] == ["character", "ascension", "floor"]
    assert payload["fallback_used"] is False


def test_recommendation_endpoint_falls_back_to_global_when_context_missing(
    client_and_engine,
):
    client, engine = client_and_engine
    with Session(engine) as session:
        session.add_all(
            [
                Run(id="run-1", win=True, character="SILENT", ascension=1),
                Run(id="run-2", win=False, character="SILENT", ascension=1),
                Run(id="run-3", win=True, character="SILENT", ascension=1),
            ]
        )
        session.add_all(
            [
                CardChoice(
                    run_id="run-1",
                    floor=1,
                    offered_cards=["CARD.BASH", "CARD.CLOTHESLINE"],
                    picked_card="CARD.CLOTHESLINE",
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

    response = client.get(
        "/recommendation?cards=CARD.BASH,CARD.CLOTHESLINE&character=IRONCLAD&ascension=10&floor=5"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["scope"] == "global"
    assert payload["fallback_used"] is True
    assert payload["reason"] == "fallback_global_no_context"


def test_live_context_endpoint_returns_unavailable_when_no_card_choices(
    client_and_engine,
):
    client, _ = client_and_engine

    response = client.get("/live/context")

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "available": False,
        "run_id": None,
        "character": None,
        "ascension": None,
        "floor": None,
        "offered_cards": [],
        "picked_card": None,
    }


def test_live_context_endpoint_returns_latest_card_choice(client_and_engine):
    client, engine = client_and_engine
    with Session(engine) as session:
        session.add_all(
            [
                Run(id="run-1", character="IRONCLAD", ascension=5, win=False),
                Run(id="run-2", character="SILENT", ascension=10, win=True),
            ]
        )
        session.add_all(
            [
                CardChoice(
                    run_id="run-1",
                    floor=3,
                    offered_cards=["CARD.A", "CARD.B"],
                    picked_card="CARD.A",
                    is_shop=False,
                ),
                CardChoice(
                    run_id="run-2",
                    floor=7,
                    offered_cards=["CARD.C", "CARD.D"],
                    picked_card="CARD.D",
                    is_shop=False,
                ),
            ]
        )
        session.commit()

    response = client.get("/live/context")

    assert response.status_code == 200
    payload = response.json()
    assert payload["available"] is True
    assert payload["run_id"] == "run-2"
    assert payload["character"] == "SILENT"
    assert payload["ascension"] == 10
    assert payload["floor"] == 7
    assert payload["offered_cards"] == ["CARD.C", "CARD.D"]
    assert payload["picked_card"] == "CARD.D"
