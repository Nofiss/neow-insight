from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


API_URL = "http://127.0.0.1:8010"


def _get_json(url: str) -> dict[str, object]:
    with urllib.request.urlopen(url, timeout=3) as response:
        body = response.read().decode("utf-8")
    return json.loads(body)


def _wait_for_health(timeout_seconds: int = 20) -> None:
    deadline = time.time() + timeout_seconds
    health_url = f"{API_URL}/health"

    while time.time() < deadline:
        try:
            payload = _get_json(health_url)
            if payload.get("status") == "ok":
                return
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            pass
        time.sleep(0.4)

    raise RuntimeError("backend healthcheck timeout")


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
    if not backend_dir.exists():
        print("backend directory not found")
        return 1

    backend_cmd = [
        "uv",
        "run",
        "uvicorn",
        "api.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8010",
    ]

    backend_proc = subprocess.Popen(backend_cmd, cwd=backend_dir)
    try:
        _wait_for_health()

        stats = _get_json(f"{API_URL}/runs/stats")
        if "total_runs" not in stats or "win_rate" not in stats:
            raise RuntimeError("invalid /runs/stats payload")

        cards = urllib.parse.quote("CARD.BASH,CARD.CLOTHESLINE")
        recommendation = _get_json(f"{API_URL}/recommendation?cards={cards}")
        if "best_pick" not in recommendation or "confidence" not in recommendation:
            raise RuntimeError("invalid /recommendation payload")

        print("e2e ok")
        print(f"stats: total_runs={stats['total_runs']} win_rate={stats['win_rate']}")
        print(
            "recommendation: "
            f"best_pick={recommendation['best_pick']} confidence={recommendation['confidence']}"
        )
        return 0
    except Exception as exc:
        print(f"e2e failed: {exc}")
        return 1
    finally:
        _terminate(backend_proc)


if __name__ == "__main__":
    raise SystemExit(main())
