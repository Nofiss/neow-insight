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
