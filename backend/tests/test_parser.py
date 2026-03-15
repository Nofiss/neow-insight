from __future__ import annotations

import json

import pytest

from core.ingestion.parser import RunParseError, parse_run_file


def test_parse_run_file_maps_core_fields(tmp_path):
    run_file = tmp_path / "sample.run"
    payload = {
        "run_id": "run-001",
        "character_chosen": "IRONCLAD",
        "ascension_level": 10,
        "seed_played": "ABC123",
        "victory": True,
        "card_choices": [
            {
                "floor": 3,
                "picked": "CARD.BASH",
                "not_picked": ["CARD.CLOTHESLINE", "CARD.POMMEL_STRIKE"],
                "is_shop": False,
            },
            {"floor": "bad", "picked": "CARD.SKIP"},
        ],
        "relics_obtained": [
            "RELIC.BURNING_BLOOD",
            {"key": "RELIC.ANCHOR", "floor": 7},
        ],
    }
    run_file.write_text(json.dumps(payload), encoding="utf-8")

    parsed = parse_run_file(run_file)

    assert parsed.run_id == "run-001"
    assert parsed.character == "IRONCLAD"
    assert parsed.ascension == 10
    assert parsed.seed == "ABC123"
    assert parsed.win is True
    assert parsed.raw_timestamp is None
    assert parsed.raw_payload["character_chosen"] == "IRONCLAD"
    assert len(parsed.card_choices) == 1
    assert parsed.card_choices[0].offered_cards == [
        "CARD.CLOTHESLINE",
        "CARD.POMMEL_STRIKE",
    ]
    assert [r.relic_id for r in parsed.relic_history] == [
        "RELIC.BURNING_BLOOD",
        "RELIC.ANCHOR",
    ]
    assert [r.floor for r in parsed.relic_history] == [1, 7]


def test_parse_run_file_invalid_json_raises(tmp_path):
    run_file = tmp_path / "broken.run"
    run_file.write_text("{not-json}", encoding="utf-8")

    with pytest.raises(RunParseError):
        parse_run_file(run_file)


def test_parse_run_file_extracts_string_timestamp(tmp_path):
    run_file = tmp_path / "sample.run"
    payload = {
        "run_id": "run-002",
        "timestamp": "2026-03-14T10:00:00Z",
        "victory": False,
    }
    run_file.write_text(json.dumps(payload), encoding="utf-8")

    parsed = parse_run_file(run_file)

    assert parsed.raw_timestamp == "2026-03-14T10:00:00Z"


def test_parse_run_file_extracts_numeric_timestamp_fallback(tmp_path):
    run_file = tmp_path / "sample.run"
    payload = {
        "run_id": "run-003",
        "playtime": 12345,
        "victory": False,
    }
    run_file.write_text(json.dumps(payload), encoding="utf-8")

    parsed = parse_run_file(run_file)

    assert parsed.raw_timestamp == "12345"


def test_parse_run_file_maps_sts2_fields_and_choices(tmp_path):
    run_file = tmp_path / "sample-sts2.run"
    payload = {
        "ascension": 0,
        "seed": 1772926310,
        "win": True,
        "start_time": "2026-03-14T14:20:00Z",
        "players": [
            {
                "id": 1,
                "character": "CHARACTER.NECROBINDER",
                "relics": ["RELIC.STARTER"],
            }
        ],
        "map_point_history": [
            [
                {
                    "map_point_type": "monster",
                    "player_stats": [
                        {
                            "card_choices": [
                                {"card": {"id": "CARD.A"}, "was_picked": False},
                                {"card": {"id": "CARD.B"}, "was_picked": True},
                                {"card": {"id": "CARD.C"}, "was_picked": False},
                            ],
                            "relic_choices": [
                                {"choice": "RELIC.FIRST", "was_picked": True}
                            ],
                        }
                    ],
                },
                {
                    "map_point_type": "shop",
                    "player_stats": [
                        {
                            "card_choices": [
                                {"card": {"id": "CARD.SHOP_1"}, "was_picked": False},
                                {"card": {"id": "CARD.SHOP_2"}, "was_picked": True},
                            ]
                        }
                    ],
                },
            ]
        ],
    }
    run_file.write_text(json.dumps(payload), encoding="utf-8")

    parsed = parse_run_file(run_file)

    assert parsed.character == "CHARACTER.NECROBINDER"
    assert parsed.ascension == 0
    assert parsed.seed == "1772926310"
    assert parsed.win is True
    assert parsed.raw_timestamp == "2026-03-14T14:20:00Z"
    assert len(parsed.card_choices) == 2
    assert parsed.card_choices[0].floor == 1
    assert parsed.card_choices[0].offered_cards == ["CARD.A", "CARD.B", "CARD.C"]
    assert parsed.card_choices[0].picked_card == "CARD.B"
    assert parsed.card_choices[0].is_shop is False
    assert parsed.card_choices[1].floor == 2
    assert parsed.card_choices[1].picked_card == "CARD.SHOP_2"
    assert parsed.card_choices[1].is_shop is True
    assert [r.relic_id for r in parsed.relic_history] == [
        "RELIC.STARTER",
        "RELIC.FIRST",
    ]


def test_parse_run_file_uses_sts2_character_id_when_character_missing(tmp_path):
    run_file = tmp_path / "sample-sts2-character-id.run"
    payload = {
        "ascension": 1,
        "win": False,
        "players": [
            {
                "id": 1,
                "character_id": "CHARACTER.REGENT",
                "relics": ["RELIC.STARTER"],
            }
        ],
    }
    run_file.write_text(json.dumps(payload), encoding="utf-8")

    parsed = parse_run_file(run_file)

    assert parsed.character == "CHARACTER.REGENT"
