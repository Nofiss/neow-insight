from __future__ import annotations

from pathlib import Path
import importlib.util
import subprocess
import sys

import pytest


def _load_reset_settings_module():
    repo_root = Path(__file__).resolve().parents[2]
    module_path = repo_root / "scripts" / "reset_settings.py"
    spec = importlib.util.spec_from_file_location("reset_settings", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_resolve_backup_path_accepts_plain_filename(tmp_path: Path):
    module = _load_reset_settings_module()

    resolved = module._resolve_backup_path(tmp_path, "settings.toml.backup-custom")

    assert resolved == tmp_path / "settings.toml.backup-custom"


def test_resolve_backup_path_rejects_nested_path(tmp_path: Path):
    module = _load_reset_settings_module()

    with pytest.raises(ValueError):
        module._resolve_backup_path(tmp_path, "nested/path.toml")


def test_resolve_backup_path_rejects_absolute_path(tmp_path: Path):
    module = _load_reset_settings_module()

    absolute_name = str((tmp_path / "outside.toml").resolve())
    with pytest.raises(ValueError):
        module._resolve_backup_path(tmp_path, absolute_name)


def test_script_returns_code_2_for_invalid_backup_name():
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts" / "reset_settings.py"

    result = subprocess.run(
        [sys.executable, str(script_path), "--backup-name", "nested/path.toml"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "--backup-name must be a plain filename" in result.stdout
