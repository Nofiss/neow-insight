from __future__ import annotations

import shutil
from pathlib import Path


def main() -> int:
    workspace_root = Path(__file__).resolve().parents[1]
    source = workspace_root / "settings.toml.example"
    target = workspace_root / "settings.toml"

    if target.exists():
        print("settings.toml already exists")
        return 0

    if not source.exists():
        print("settings.toml.example not found")
        return 1

    shutil.copyfile(source, target)
    print("created settings.toml from settings.toml.example")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
