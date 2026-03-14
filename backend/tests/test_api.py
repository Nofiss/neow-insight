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


def test_runs_list_endpoint_returns_paginated_runs(client_and_engine):
    client, engine = client_and_engine
    with Session(engine) as session:
        session.add_all(
            [
                Run(
                    id="run-1",
                    character="IRONCLAD",
                    ascension=5,
                    win=True,
                    raw_timestamp="2026-01-02T10:00:00Z",
                    imported_at="2026-01-02T10:05:00Z",
                    source_file="first.run",
                    raw_payload={"run_id": "run-1"},
                ),
                Run(
                    id="run-2",
                    character="SILENT",
                    ascension=2,
                    win=False,
                    raw_timestamp="2026-01-03T10:00:00Z",
                    imported_at="2026-01-03T10:05:00Z",
                    source_file="second.run",
                    raw_payload={"run_id": "run-2"},
                ),
            ]
        )
        session.add(
            CardChoice(
                run_id="run-2",
                floor=1,
                offered_cards=["CARD.A", "CARD.B"],
                picked_card="CARD.A",
                is_shop=False,
            )
        )
        session.commit()

    response = client.get("/runs?page=1&page_size=1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["page"] == 1
    assert payload["page_size"] == 1
    assert payload["total"] == 2
    assert payload["total_pages"] == 2
    assert len(payload["items"]) == 1
    assert payload["items"][0]["run_id"] == "run-2"


def test_runs_list_endpoint_filters_by_character_and_win(client_and_engine):
    client, engine = client_and_engine
    with Session(engine) as session:
        session.add_all(
            [
                Run(
                    id="run-10",
                    character="IRONCLAD",
                    ascension=5,
                    win=True,
                    imported_at="2026-01-02T10:05:00Z",
                    raw_payload={"run_id": "run-10"},
                ),
                Run(
                    id="run-11",
                    character="IRONCLAD",
                    ascension=5,
                    win=False,
                    imported_at="2026-01-03T10:05:00Z",
                    raw_payload={"run_id": "run-11"},
                ),
            ]
        )
        session.commit()

    response = client.get("/runs?character=IRONCLAD&win=true")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["run_id"] == "run-10"


def test_run_detail_endpoint_returns_full_payload(client_and_engine):
    client, engine = client_and_engine
    with Session(engine) as session:
        session.add(
            Run(
                id="run-detail",
                character="IRONCLAD",
                ascension=10,
                win=True,
                imported_at="2026-01-03T10:05:00Z",
                raw_payload={"run_id": "run-detail", "some": "value"},
            )
        )
        session.add(
            CardChoice(
                run_id="run-detail",
                floor=3,
                offered_cards=["CARD.A", "CARD.B"],
                picked_card="CARD.A",
                is_shop=False,
            )
        )
        session.commit()

    response = client.get("/runs/run-detail")

    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"] == "run-detail"
    assert payload["raw_payload"]["some"] == "value"
    assert len(payload["card_choices"]) == 1


def test_run_timeline_endpoint_returns_sorted_events(client_and_engine):
    client, engine = client_and_engine
    with Session(engine) as session:
        session.add(
            Run(
                id="run-timeline",
                character="SILENT",
                ascension=2,
                win=False,
                imported_at="2026-01-03T10:05:00Z",
                raw_payload={"run_id": "run-timeline"},
            )
        )
        session.add_all(
            [
                CardChoice(
                    run_id="run-timeline",
                    floor=5,
                    offered_cards=["CARD.A", "CARD.B"],
                    picked_card="CARD.B",
                    is_shop=False,
                ),
                CardChoice(
                    run_id="run-timeline",
                    floor=2,
                    offered_cards=["CARD.C", "CARD.D"],
                    picked_card="CARD.C",
                    is_shop=False,
                ),
            ]
        )
        session.commit()

    response = client.get("/runs/run-timeline/timeline")

    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"] == "run-timeline"
    assert payload["events"][0]["floor"] == 2
    assert payload["events"][1]["floor"] == 5


def test_run_detail_endpoint_returns_404_for_missing_run(client_and_engine):
    client, _ = client_and_engine

    response = client.get("/runs/missing-run")

    assert response.status_code == 404


def test_run_timeline_includes_extended_events_from_raw_payload(client_and_engine):
    client, engine = client_and_engine
    with Session(engine) as session:
        session.add(
            Run(
                id="run-rich",
                character="IRONCLAD",
                ascension=12,
                win=True,
                imported_at="2026-01-03T10:05:00Z",
                raw_payload={
                    "run_id": "run-rich",
                    "campfire_choices": [{"floor": 6, "key": "REST"}],
                    "event_choices": [
                        {
                            "floor": 8,
                            "event_name": "Golden Idol",
                            "player_choice": "TAKE_DAMAGE",
                        }
                    ],
                    "potions_obtained": [{"floor": 9, "key": "POTION.FIRE"}],
                    "boss_relics": [{"picked": "RELIC.BLACK_BLOOD"}],
                },
            )
        )
        session.commit()

    response = client.get("/runs/run-rich/timeline")

    assert response.status_code == 200
    payload = response.json()
    kinds = [event["kind"] for event in payload["events"]]
    assert "campfire" in kinds
    assert "event" in kinds
    assert "potion" in kinds
    assert "boss_relic" in kinds


def test_run_completeness_endpoint_returns_field_coverage(client_and_engine):
    client, engine = client_and_engine
    with Session(engine) as session:
        session.add(
            Run(
                id="run-complete",
                character="IRONCLAD",
                ascension=12,
                win=True,
                imported_at="2026-01-03T10:05:00Z",
                raw_payload={
                    "run_id": "run-complete",
                    "score": 100,
                    "floor_reached": 20,
                    "gold": 250,
                    "card_choices": [{"floor": 1}],
                },
            )
        )
        session.commit()

    response = client.get("/runs/run-complete/completeness")

    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"] == "run-complete"
    assert payload["available"] > 0
    assert payload["total"] == 12
    assert "Campfire choices" in payload["missing"]


def test_run_completeness_endpoint_returns_404_for_missing_run(client_and_engine):
    client, _ = client_and_engine

    response = client.get("/runs/missing-run/completeness")

    assert response.status_code == 404
