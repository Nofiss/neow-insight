from __future__ import annotations

from pathlib import Path

import core.config as config_module
from core.config import _resolve_storage_paths, get_settings


def test_resolve_storage_paths_uses_saves_path_when_provided(tmp_path: Path):
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    saves_path = workspace_root / "game" / "saves"

    resolved_saves, resolved_history, resolved_current = _resolve_storage_paths(
        {"saves_path": str(saves_path)},
        workspace_root,
        workspace_root / "default" / "saves",
    )

    assert resolved_saves == saves_path
    assert resolved_history == saves_path / "history"
    assert resolved_current == saves_path / "current_run.save"


def test_resolve_storage_paths_derives_saves_from_legacy_history(tmp_path: Path):
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    history_path = workspace_root / "game" / "saves" / "history"

    resolved_saves, resolved_history, resolved_current = _resolve_storage_paths(
        {"run_history_path": str(history_path)},
        workspace_root,
        workspace_root / "default" / "saves",
    )

    assert resolved_saves == history_path.parent
    assert resolved_history == history_path
    assert resolved_current == history_path.parent / "current_run.save"


def test_resolve_storage_paths_defaults_to_default_saves(tmp_path: Path):
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    default_saves = workspace_root / "default" / "saves"

    resolved_saves, resolved_history, resolved_current = _resolve_storage_paths(
        {},
        workspace_root,
        default_saves,
    )

    assert resolved_saves == default_saves
    assert resolved_history == default_saves / "history"
    assert resolved_current == default_saves / "current_run.save"


def test_get_settings_defaults_llm_values(tmp_path: Path, monkeypatch):
    workspace = tmp_path / "workspace"
    backend = workspace / "backend"
    core = backend / "core"
    core.mkdir(parents=True)
    (core / "config.py").write_text("", encoding="utf-8")

    monkeypatch.setattr(config_module, "__file__", str(core / "config.py"))
    get_settings.cache_clear()
    settings = get_settings()

    assert settings.llm_enabled is False
    assert settings.llm_provider == "ollama"
    assert settings.llm_base_url == "http://127.0.0.1:11434"
    assert settings.llm_model == "gemma3:latest"
    assert settings.llm_timeout_ms == 1500
    get_settings.cache_clear()


def test_get_settings_reads_llm_values_from_file(tmp_path: Path, monkeypatch):
    workspace = tmp_path / "workspace"
    backend = workspace / "backend"
    core = backend / "core"
    core.mkdir(parents=True)
    (core / "config.py").write_text("", encoding="utf-8")
    (workspace / "settings.toml").write_text(
        "\n".join(
            [
                "[llm]",
                "enabled = true",
                'provider = "ollama"',
                'base_url = "http://localhost:11434"',
                'model = "llama3.1:8b"',
                "timeout_ms = 2200",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(config_module, "__file__", str(core / "config.py"))
    get_settings.cache_clear()
    settings = get_settings()

    assert settings.llm_enabled is True
    assert settings.llm_provider == "ollama"
    assert settings.llm_base_url == "http://localhost:11434"
    assert settings.llm_model == "llama3.1:8b"
    assert settings.llm_timeout_ms == 2200
    get_settings.cache_clear()
