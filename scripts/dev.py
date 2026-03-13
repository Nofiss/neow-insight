from __future__ import annotations

import signal
import subprocess
from pathlib import Path

from process_utils import resolve_command, terminate_process


BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = "8000"
FRONTEND_HOST = "127.0.0.1"
FRONTEND_PORT = "5173"


def main() -> int:
    workspace_root = Path(__file__).resolve().parents[1]
    backend_dir = workspace_root / "backend"
    frontend_dir = workspace_root / "frontend"

    if not backend_dir.exists() or not frontend_dir.exists():
        print("backend/ or frontend/ directory not found")
        return 1

    backend_cmd = ["uv", "run", "python", "-m", "scripts.api_dev"]
    frontend_cmd = [
        "pnpm",
        "run",
        "dev",
        "--",
        "--host",
        FRONTEND_HOST,
        "--port",
        FRONTEND_PORT,
    ]

    try:
        backend_cmd, backend_executable = resolve_command(backend_cmd)
    except FileNotFoundError:
        print("Could not start backend: 'uv' was not found in PATH")
        return 1

    try:
        frontend_cmd, frontend_executable = resolve_command(frontend_cmd)
    except FileNotFoundError:
        print("Could not start frontend: 'pnpm' was not found in PATH")
        return 1

    try:
        backend_proc = subprocess.Popen(backend_cmd, cwd=backend_dir)
    except FileNotFoundError:
        print(f"Could not start backend: '{backend_executable}' was not found in PATH")
        return 1

    try:
        frontend_proc = subprocess.Popen(frontend_cmd, cwd=frontend_dir)
    except FileNotFoundError:
        terminate_process(backend_proc)
        print(
            f"Could not start frontend: '{frontend_executable}' was not found in PATH"
        )
        return 1

    print(f"backend: http://localhost:{BACKEND_PORT}")
    print(f"frontend: http://localhost:{FRONTEND_PORT}")
    print("press Ctrl+C to stop")

    def stop_handler(_signum: int, _frame: object) -> None:
        terminate_process(frontend_proc)
        terminate_process(backend_proc)

    signal.signal(signal.SIGINT, stop_handler)
    signal.signal(signal.SIGTERM, stop_handler)

    try:
        backend_code = backend_proc.wait()
        frontend_code = frontend_proc.poll()
        if frontend_code is None:
            terminate_process(frontend_proc)
            frontend_code = frontend_proc.wait()
        return backend_code or frontend_code
    finally:
        terminate_process(frontend_proc)
        terminate_process(backend_proc)


if __name__ == "__main__":
    raise SystemExit(main())
