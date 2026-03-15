from __future__ import annotations

import pytest
from dataclasses import replace
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from api.main import app
from api.services import live_context as live_context_service
from api.state import ingest_status
from core.db import get_session
from core.db.models import CardChoice, Run


def _recommendation_base_url(
    cards: str, character: str, ascension: int, floor: int
) -> str:
    return (
        f"/recommendation?cards={cards}"
        f"&character={character}&ascension={ascension}&floor={floor}"
    )


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

    def reset_ingest_status() -> None:
        ingest_status.scanned = 0
        ingest_status.imported = 0
        ingest_status.updated = 0
        ingest_status.parse_errors = 0
        ingest_status.skipped = 0
        ingest_status.recent_issues = []
        ingest_status.last_processed_run_id = None
        ingest_status.last_processed_file = None
        ingest_status.last_event_at = None

    live_context_service.clear_recovered_live_cards()

    reset_ingest_status()
    try:
        with TestClient(app) as client:
            reset_ingest_status()
            yield client, engine
    finally:
        live_context_service.clear_recovered_live_cards()
        app.dependency_overrides.clear()
        reset_ingest_status()


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
    assert payload["llm_pick"] is None
    assert payload["llm_used"] is False
    assert payload["source"] == "statistical"


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
    assert payload["llm_pick"] is None
    assert payload["llm_used"] is False
    assert payload["source"] == "statistical"


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


def test_recommendation_endpoint_live_hybrid_llm_disabled_sets_fallback_fields(
    client_and_engine,
    monkeypatch,
):
    from api.routers import recommendation as recommendation_router

    monkeypatch.setattr(
        recommendation_router,
        "settings",
        replace(recommendation_router.settings, llm_enabled=False),
    )

    client, engine = client_and_engine
    with Session(engine) as session:
        session.add(
            Run(
                id="run-live-llm-off",
                character="IRONCLAD",
                ascension=5,
                win=False,
                imported_at="2026-03-15T10:00:00Z",
                raw_payload={"run_id": "run-live-llm-off", "floor_reached": 9},
            )
        )
        session.add(
            CardChoice(
                run_id="run-live-llm-off",
                floor=9,
                offered_cards=["CARD.A", "CARD.B"],
                picked_card="CARD.A",
                is_shop=False,
            )
        )
        session.commit()

    response = client.get(_recommendation_base_url("CARD.A,CARD.B", "IRONCLAD", 5, 9))

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "hybrid_fallback"
    assert payload["llm_used"] is False
    assert payload["llm_pick"] is None
    assert payload["llm_error"] == "llm_disabled"


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


def test_live_context_endpoint_returns_most_recent_imported_run(client_and_engine):
    client, engine = client_and_engine
    with Session(engine) as session:
        session.add_all(
            [
                Run(
                    id="run-older",
                    character="IRONCLAD",
                    ascension=5,
                    win=False,
                    imported_at="2026-01-01T10:00:00Z",
                ),
                Run(
                    id="run-current",
                    character="SILENT",
                    ascension=10,
                    win=True,
                    imported_at="2026-01-02T10:00:00Z",
                ),
            ]
        )
        session.add_all(
            [
                CardChoice(
                    run_id="run-current",
                    floor=4,
                    offered_cards=["CARD.X", "CARD.Y"],
                    picked_card="CARD.X",
                    is_shop=False,
                ),
                CardChoice(
                    run_id="run-older",
                    floor=3,
                    offered_cards=["CARD.A", "CARD.B"],
                    picked_card="CARD.A",
                    is_shop=False,
                ),
                CardChoice(
                    run_id="run-current",
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
    assert payload["run_id"] == "run-current"
    assert payload["character"] == "SILENT"
    assert payload["ascension"] == 10
    assert payload["floor"] == 7
    assert payload["offered_cards"] == ["CARD.C", "CARD.D"]
    assert payload["picked_card"] == "CARD.D"


def test_live_context_endpoint_exposes_run_context_without_card_choices(
    client_and_engine,
):
    client, engine = client_and_engine
    with Session(engine) as session:
        session.add(
            Run(
                id="run-live-no-cards",
                character="CHARACTER.IRONCLAD",
                ascension=15,
                win=False,
                imported_at="2026-03-15T00:00:00Z",
                raw_payload={"run_id": "run-live-no-cards", "floor_reached": 23},
            )
        )
        session.commit()

    response = client.get("/live/context")

    assert response.status_code == 200
    payload = response.json()
    assert payload["available"] is True
    assert payload["run_id"] == "run-live-no-cards"
    assert payload["character"] == "CHARACTER.IRONCLAD"
    assert payload["ascension"] == 15
    assert payload["floor"] == 23
    assert payload["offered_cards"] == []
    assert payload["picked_card"] is None


def test_live_context_endpoint_uses_sts2_floor_when_floor_reached_missing(
    client_and_engine,
):
    client, engine = client_and_engine
    with Session(engine) as session:
        session.add(
            Run(
                id="run-live-sts2",
                character="CHARACTER.NECROBINDER",
                ascension=2,
                win=False,
                imported_at="2026-03-15T01:00:00Z",
                raw_payload={
                    "run_id": "run-live-sts2",
                    "map_point_history": [
                        [{"map_point_type": "monster"}, {"map_point_type": "shop"}],
                        [{"map_point_type": "event"}],
                    ],
                },
            )
        )
        session.commit()

    response = client.get("/live/context")

    assert response.status_code == 200
    payload = response.json()
    assert payload["available"] is True
    assert payload["run_id"] == "run-live-sts2"
    assert payload["character"] == "CHARACTER.NECROBINDER"
    assert payload["ascension"] == 2
    assert payload["floor"] == 3
    assert payload["offered_cards"] == []
    assert payload["picked_card"] is None


def test_live_context_endpoint_exposes_pending_sts2_card_reward(
    client_and_engine,
):
    client, engine = client_and_engine
    with Session(engine) as session:
        session.add(
            Run(
                id="run-live-pending-reward",
                character="CHARACTER.WATCHER",
                ascension=2,
                win=False,
                imported_at="2026-03-15T02:00:00Z",
                raw_payload={
                    "run_id": "run-live-pending-reward",
                    "map_point_history": [
                        [
                            {"map_point_type": "monster"},
                            {
                                "map_point_type": "monster",
                                "player_stats": [
                                    {
                                        "card_choices": [
                                            {
                                                "card": {"id": "CARD.PALE_BLUE_DOT"},
                                                "was_picked": False,
                                            },
                                            {
                                                "card": {"id": "CARD.BATTLE_LOOT"},
                                                "was_picked": False,
                                            },
                                            {
                                                "card": {"id": "CARD.TERRAFORM"},
                                                "was_picked": False,
                                            },
                                        ]
                                    }
                                ],
                            },
                        ]
                    ],
                },
            )
        )
        session.commit()

    response = client.get("/live/context")

    assert response.status_code == 200
    payload = response.json()
    assert payload["available"] is True
    assert payload["run_id"] == "run-live-pending-reward"
    assert payload["character"] == "CHARACTER.WATCHER"
    assert payload["ascension"] == 2
    assert payload["floor"] == 2
    assert payload["offered_cards"] == [
        "CARD.PALE_BLUE_DOT",
        "CARD.BATTLE_LOOT",
        "CARD.TERRAFORM",
    ]
    assert payload["picked_card"] is None


def test_live_context_endpoint_tiebreaks_with_run_id_when_recency_is_equal(
    client_and_engine,
):
    client, engine = client_and_engine
    with Session(engine) as session:
        session.add_all(
            [
                Run(
                    id="run-a",
                    character="IRONCLAD",
                    ascension=2,
                    win=False,
                    imported_at="2026-01-03T10:00:00Z",
                ),
                Run(
                    id="run-b",
                    character="WATCHER",
                    ascension=3,
                    win=True,
                    imported_at="2026-01-03T10:00:00Z",
                ),
            ]
        )
        session.add_all(
            [
                CardChoice(
                    run_id="run-a",
                    floor=2,
                    offered_cards=["CARD.A1", "CARD.A2"],
                    picked_card="CARD.A1",
                    is_shop=False,
                ),
                CardChoice(
                    run_id="run-b",
                    floor=5,
                    offered_cards=["CARD.B1", "CARD.B2"],
                    picked_card="CARD.B2",
                    is_shop=False,
                ),
            ]
        )
        session.commit()

    response = client.get("/live/context")

    assert response.status_code == 200
    payload = response.json()
    assert payload["available"] is True
    assert payload["run_id"] == "run-b"
    assert payload["character"] == "WATCHER"
    assert payload["ascension"] == 3
    assert payload["floor"] == 5
    assert payload["offered_cards"] == ["CARD.B1", "CARD.B2"]
    assert payload["picked_card"] == "CARD.B2"


def test_live_recover_cards_endpoint_returns_live_unavailable_when_no_run(
    client_and_engine,
):
    client, _ = client_and_engine

    response = client.post("/live/recover-cards", json={"image_base64": "abc"})

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "success": False,
        "offered_cards": [],
        "source": "live_unavailable",
        "llm_model": None,
        "llm_error": "live_unavailable",
    }


def test_live_recover_cards_endpoint_returns_save_cards_when_present(
    client_and_engine,
):
    client, engine = client_and_engine
    with Session(engine) as session:
        session.add(
            Run(
                id="run-live-save-cards",
                character="IRONCLAD",
                ascension=3,
                win=False,
                imported_at="2026-03-15T03:00:00Z",
                raw_payload={"run_id": "run-live-save-cards", "floor_reached": 4},
            )
        )
        session.add(
            CardChoice(
                run_id="run-live-save-cards",
                floor=4,
                offered_cards=["CARD.A", "CARD.B", "CARD.C"],
                picked_card="CARD.A",
                is_shop=False,
            )
        )
        session.commit()

    response = client.post("/live/recover-cards", json={"image_base64": "abc"})

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "success": True,
        "offered_cards": ["CARD.A", "CARD.B", "CARD.C"],
        "source": "save",
        "llm_model": None,
        "llm_error": None,
    }


def test_live_recover_cards_endpoint_uses_llm_and_updates_live_context(
    client_and_engine,
    monkeypatch,
):
    from api.services import live_card_recovery

    client, engine = client_and_engine
    with Session(engine) as session:
        session.add(
            Run(
                id="run-live-recover",
                character="WATCHER",
                ascension=2,
                win=False,
                imported_at="2026-03-15T04:00:00Z",
                raw_payload={"run_id": "run-live-recover", "floor_reached": 6},
            )
        )
        session.commit()

    class _StubResponse:
        def __init__(self):
            self.payload = {
                "offered_cards": ["card.alpha", "CARD.BETA", "Card beta", "CARD.GAMMA"]
            }
            self.model = "gemma:8b"

    class _StubClient:
        def __init__(self, *, base_url: str, model: str, timeout_ms: int) -> None:
            self.base_url = base_url
            self.model = model
            self.timeout_ms = timeout_ms

        def complete_json_with_image(
            self, *, prompt: str, system_prompt: str, image_base64: str
        ):
            return _StubResponse()

    monkeypatch.setattr(live_card_recovery, "LlmClient", _StubClient)

    response = client.post("/live/recover-cards", json={"image_base64": "abc"})

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "success": True,
        "offered_cards": ["CARD.ALPHA", "CARD.BETA", "CARD.GAMMA"],
        "source": "llm_vision",
        "llm_model": "gemma:8b",
        "llm_error": None,
    }

    live_context_response = client.get("/live/context")
    assert live_context_response.status_code == 200
    live_payload = live_context_response.json()
    assert live_payload["offered_cards"] == ["CARD.ALPHA", "CARD.BETA", "CARD.GAMMA"]


def test_live_recover_cards_endpoint_returns_llm_error_when_invalid_payload(
    client_and_engine,
    monkeypatch,
):
    from api.services import live_card_recovery

    client, engine = client_and_engine
    with Session(engine) as session:
        session.add(
            Run(
                id="run-live-recover-invalid",
                character="SILENT",
                ascension=1,
                win=False,
                imported_at="2026-03-15T05:00:00Z",
                raw_payload={"run_id": "run-live-recover-invalid", "floor_reached": 8},
            )
        )
        session.commit()

    class _StubResponse:
        def __init__(self):
            self.payload = {"wrong": []}
            self.model = "gemma:8b"

    class _StubClient:
        def __init__(self, *, base_url: str, model: str, timeout_ms: int) -> None:
            self.base_url = base_url
            self.model = model
            self.timeout_ms = timeout_ms

        def complete_json_with_image(
            self, *, prompt: str, system_prompt: str, image_base64: str
        ):
            return _StubResponse()

    monkeypatch.setattr(live_card_recovery, "LlmClient", _StubClient)

    response = client.post("/live/recover-cards", json={"image_base64": "abc"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is False
    assert payload["offered_cards"] == []
    assert payload["source"] == "llm_vision"
    assert payload["llm_model"] == "gemma:8b"
    assert payload["llm_error"] is not None


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


def test_runs_list_endpoint_handles_blank_imported_at(client_and_engine):
    client, engine = client_and_engine
    with Session(engine) as session:
        session.add(
            Run(
                id="run-null-imported-at-list",
                character="IRONCLAD",
                ascension=1,
                win=True,
                raw_timestamp="2026-02-01T10:00:00Z",
                imported_at="",
                raw_payload={"run_id": "run-null-imported-at-list"},
            )
        )
        session.commit()

    response = client.get("/runs?page=1&page_size=20")

    assert response.status_code == 200
    payload = response.json()
    item = next(
        candidate
        for candidate in payload["items"]
        if candidate["run_id"] == "run-null-imported-at-list"
    )
    assert item["imported_at"] == "2026-02-01T10:00:00Z"


def test_runs_characters_endpoint_returns_distinct_sorted_values(client_and_engine):
    client, engine = client_and_engine
    with Session(engine) as session:
        session.add_all(
            [
                Run(id="run-character-1", character="SILENT", win=True),
                Run(id="run-character-2", character="IRONCLAD", win=False),
                Run(id="run-character-3", character="SILENT", win=False),
                Run(id="run-character-4", character="CHARACTER.NECROBINDER", win=True),
                Run(id="run-character-5", character="  ", win=True),
                Run(id="run-character-6", character=None, win=True),
            ]
        )
        session.commit()

    response = client.get("/runs/characters")

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "items": [
            "CHARACTER.NECROBINDER",
            "IRONCLAD",
            "SILENT",
        ]
    }


def test_runs_characters_endpoint_returns_empty_when_no_runs(client_and_engine):
    client, _ = client_and_engine

    response = client.get("/runs/characters")

    assert response.status_code == 200
    payload = response.json()
    assert payload == {"items": []}


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


def test_run_detail_endpoint_handles_blank_imported_at(client_and_engine):
    client, engine = client_and_engine
    with Session(engine) as session:
        session.add(
            Run(
                id="run-null-imported-at-detail",
                character="SILENT",
                ascension=3,
                win=False,
                raw_timestamp="2026-02-02T10:00:00Z",
                imported_at="",
                raw_payload={"run_id": "run-null-imported-at-detail"},
            )
        )
        session.commit()

    response = client.get("/runs/run-null-imported-at-detail")

    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"] == "run-null-imported-at-detail"
    assert payload["imported_at"] == "2026-02-02T10:00:00Z"


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
    assert payload["available_direct"] > 0
    assert payload["available_inferred"] >= 0
    assert (
        payload["available"]
        == payload["available_direct"] + payload["available_inferred"]
    )
    assert payload["total"] == 12
    assert "Campfire choices" in payload["missing"]
    assert "Campfire choices" not in payload["inferred"]


def test_run_completeness_endpoint_returns_404_for_missing_run(client_and_engine):
    client, _ = client_and_engine

    response = client.get("/runs/missing-run/completeness")

    assert response.status_code == 404


def test_run_timeline_includes_sts2_mapped_events(client_and_engine):
    client, engine = client_and_engine
    with Session(engine) as session:
        session.add(
            Run(
                id="run-sts2-timeline",
                character="CHARACTER.NECROBINDER",
                ascension=0,
                win=True,
                imported_at="2026-01-03T10:05:00Z",
                raw_payload={
                    "run_id": "run-sts2-timeline",
                    "run_time": 1400,
                    "map_point_history": [
                        [
                            {
                                "map_point_type": "monster",
                                "player_stats": [
                                    {
                                        "current_gold": 99,
                                        "current_hp": 66,
                                        "max_hp": 66,
                                        "card_choices": [
                                            {
                                                "card": {"id": "CARD.A"},
                                                "was_picked": False,
                                            },
                                            {
                                                "card": {"id": "CARD.B"},
                                                "was_picked": True,
                                            },
                                        ],
                                        "potion_choices": [
                                            {
                                                "choice": "POTION.FIRE",
                                                "was_picked": True,
                                            }
                                        ],
                                    }
                                ],
                            },
                            {
                                "map_point_type": "rest_site",
                                "player_stats": [
                                    {
                                        "current_gold": 120,
                                        "current_hp": 60,
                                        "max_hp": 66,
                                        "rest_site_choices": ["SMITH"],
                                    }
                                ],
                            },
                            {
                                "map_point_type": "unknown",
                                "player_stats": [
                                    {
                                        "current_gold": 130,
                                        "current_hp": 58,
                                        "max_hp": 66,
                                        "event_choices": [
                                            {
                                                "title": {
                                                    "key": "EVENT.TEST",
                                                    "table": "events",
                                                }
                                            }
                                        ],
                                    }
                                ],
                            },
                            {
                                "map_point_type": "boss",
                                "player_stats": [
                                    {
                                        "current_gold": 200,
                                        "current_hp": 40,
                                        "max_hp": 66,
                                        "potion_used": ["POTION.FIRE"],
                                        "relic_choices": [
                                            {
                                                "choice": "RELIC.BOSS",
                                                "was_picked": True,
                                            }
                                        ],
                                    }
                                ],
                            },
                        ]
                    ],
                },
            )
        )
        session.commit()

    response = client.get("/runs/run-sts2-timeline/timeline")

    assert response.status_code == 200
    payload = response.json()
    kinds = [event["kind"] for event in payload["events"]]
    assert "campfire" in kinds
    assert "event" in kinds
    assert "potion" in kinds
    assert "boss_relic" in kinds


def test_run_completeness_endpoint_maps_sts2_fields(client_and_engine):
    client, engine = client_and_engine
    with Session(engine) as session:
        session.add(
            Run(
                id="run-sts2-completeness",
                character="CHARACTER.NECROBINDER",
                ascension=0,
                win=True,
                imported_at="2026-01-03T10:05:00Z",
                raw_payload={
                    "run_id": "run-sts2-completeness",
                    "run_time": 1400,
                    "map_point_history": [
                        [
                            {
                                "map_point_type": "monster",
                                "player_stats": [
                                    {
                                        "current_gold": 99,
                                        "current_hp": 66,
                                        "max_hp": 66,
                                        "card_choices": [
                                            {
                                                "card": {"id": "CARD.A"},
                                                "was_picked": True,
                                            }
                                        ],
                                        "potion_choices": [
                                            {
                                                "choice": "POTION.FIRE",
                                                "was_picked": True,
                                            }
                                        ],
                                    }
                                ],
                            },
                            {
                                "map_point_type": "rest_site",
                                "player_stats": [{"rest_site_choices": ["REST"]}],
                            },
                            {
                                "map_point_type": "unknown",
                                "player_stats": [
                                    {
                                        "event_choices": [
                                            {
                                                "title": {
                                                    "key": "EVENT.TEST",
                                                    "table": "events",
                                                }
                                            }
                                        ]
                                    }
                                ],
                            },
                            {
                                "map_point_type": "boss",
                                "player_stats": [
                                    {
                                        "relic_choices": [
                                            {
                                                "choice": "RELIC.BOSS",
                                                "was_picked": True,
                                            }
                                        ]
                                    }
                                ],
                            },
                        ]
                    ],
                },
            )
        )
        session.commit()

    response = client.get("/runs/run-sts2-completeness/completeness")

    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"] == "run-sts2-completeness"
    assert (
        payload["available"]
        == payload["available_direct"] + payload["available_inferred"]
    )
    assert payload["available_inferred"] > 0
    assert payload["total"] == 12
    assert "Score" in payload["missing"]
    assert "Campfire choices" not in payload["missing"]
    assert "Event choices" not in payload["missing"]
    assert "Card choices" not in payload["missing"]
    assert "Boss relics" not in payload["missing"]
    assert "Potions obtained" not in payload["missing"]
    assert "Campfire choices" in payload["inferred"]
    assert "Event choices" in payload["inferred"]
    assert "Card choices" in payload["inferred"]
    assert "Boss relics" in payload["inferred"]
    assert "Potions obtained" in payload["inferred"]
