from __future__ import annotations

import signal
import sys
import time
from pathlib import Path

from core.config import get_settings
from core.db import init_db
from core.db.session import engine
from core.ingestion.importer import import_run_file
from core.watcher import start_watcher
from sqlmodel import Session


def process_path(run_path: Path) -> None:
    with Session(engine) as session:
        report = import_run_file(run_path, session)
    print(
        f"watch update path={run_path} imported={report.imported} updated={report.updated}"
    )


def main() -> None:
    settings = get_settings()
    init_db()

    history_exists = settings.run_history_path.exists()
    current_exists = settings.current_run_path.exists()
    if not history_exists and not current_exists:
        print(
            "no watch target found "
            f"history={settings.run_history_path} "
            f"current={settings.current_run_path}"
        )
        sys.exit(1)

    observer = start_watcher(
        settings.run_history_path,
        settings.current_run_path,
        process_path,
    )
    print(
        "watching "
        f"history={settings.run_history_path} "
        f"current={settings.current_run_path}"
    )

    def stop_handler(_signum: int, _frame: object) -> None:
        observer.stop()

    signal.signal(signal.SIGINT, stop_handler)
    signal.signal(signal.SIGTERM, stop_handler)

    try:
        while observer.is_alive():
            time.sleep(0.5)
    finally:
        observer.join()


if __name__ == "__main__":
    main()
