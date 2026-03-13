from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def _run(command: list[str], *, cwd: Path, label: str) -> int:
    print(f"[verify] {label}")
    executable = command[0]
    if sys.platform == "win32" and executable == "pnpm":
        executable = "pnpm.cmd"
    resolved = shutil.which(executable)
    if not resolved:
        print(f"[verify] executable not found: {executable}")
        return 1

    command = [resolved, *command[1:]]
    result = subprocess.run(command, cwd=cwd)
    return result.returncode


def main() -> int:
    workspace_root = Path(__file__).resolve().parents[1]
    backend_dir = workspace_root / "backend"
    frontend_dir = workspace_root / "frontend"

    if not backend_dir.exists() or not frontend_dir.exists():
        print("backend/ or frontend/ directory not found")
        return 1

    steps = [
        (backend_dir, ["uv", "run", "ruff", "check", "."], "backend lint"),
        (backend_dir, ["uv", "run", "pytest"], "backend tests"),
        (frontend_dir, ["pnpm", "run", "lint"], "frontend lint"),
        (frontend_dir, ["pnpm", "run", "build"], "frontend build"),
    ]

    for cwd, command, label in steps:
        code = _run(command, cwd=cwd, label=label)
        if code != 0:
            print(f"[verify] failed at: {label}")
            return code

    print("[verify] all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
