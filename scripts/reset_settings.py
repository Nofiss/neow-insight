from __future__ import annotations

import argparse
from datetime import datetime
import shutil
from pathlib import Path


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reset settings.toml from settings.toml.example"
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="overwrite settings.toml without creating a backup",
    )
    parser.add_argument(
        "--backup-name",
        type=str,
        default="",
        help="custom backup filename (used only when backup is enabled)",
    )
    return parser.parse_args()


def _resolve_backup_path(workspace_root: Path, backup_name: str) -> Path:
    name = backup_name.strip()
    if not name:
        return workspace_root / f"settings.toml.backup-{_timestamp()}"

    candidate = Path(name)
    if candidate.is_absolute() or candidate.name != name:
        raise ValueError("--backup-name must be a plain filename in repository root")
    return workspace_root / candidate


def main() -> int:
    args = _parse_args()
    workspace_root = Path(__file__).resolve().parents[1]
    source = workspace_root / "settings.toml.example"
    target = workspace_root / "settings.toml"

    if not source.exists():
        print("settings.toml.example not found")
        return 1

    if target.exists() and not args.no_backup:
        try:
            backup = _resolve_backup_path(workspace_root, args.backup_name)
        except ValueError as exc:
            print(str(exc))
            return 2
        shutil.copyfile(target, backup)
        print(f"backup created: {backup.name}")

    shutil.copyfile(source, target)
    print("settings.toml reset from settings.toml.example")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
