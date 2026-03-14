from __future__ import annotations

from pathlib import Path

from core.config import _resolve_storage_paths


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
