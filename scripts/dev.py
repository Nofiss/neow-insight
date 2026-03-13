from __future__ import annotations

import signal
import subprocess
import sys
from pathlib import Path


def _terminate(proc: subprocess.Popen[bytes]) -> None:
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


def main() -> int:
    workspace_root = Path(__file__).resolve().parents[1]
    backend_dir = workspace_root / "backend"
    frontend_dir = workspace_root / "frontend"

    if not backend_dir.exists() or not frontend_dir.exists():
        print("backend/ or frontend/ directory not found")
        return 1

    backend_cmd = ["uv", "run", "api-dev"]
    frontend_cmd = ["pnpm", "run", "dev", "--", "--host", "127.0.0.1", "--port", "5173"]

    backend_proc = subprocess.Popen(backend_cmd, cwd=backend_dir)
    frontend_proc = subprocess.Popen(frontend_cmd, cwd=frontend_dir)

    print("backend: http://127.0.0.1:8000")
    print("frontend: http://127.0.0.1:5173")
    print("press Ctrl+C to stop")

    def stop_handler(_signum: int, _frame: object) -> None:
        _terminate(frontend_proc)
        _terminate(backend_proc)

    signal.signal(signal.SIGINT, stop_handler)
    signal.signal(signal.SIGTERM, stop_handler)

    try:
        backend_code = backend_proc.wait()
        frontend_code = frontend_proc.poll()
        if frontend_code is None:
            _terminate(frontend_proc)
            frontend_code = frontend_proc.wait()
        return backend_code or frontend_code
    finally:
        _terminate(frontend_proc)
        _terminate(backend_proc)


if __name__ == "__main__":
    raise SystemExit(main())
