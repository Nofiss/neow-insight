from __future__ import annotations

from core.config import get_settings
from core.db import init_db
from core.db.session import engine
from core.ingestion.importer import import_history
from sqlmodel import Session


def main() -> None:
    settings = get_settings()
    init_db()
    with Session(engine) as session:
        report = import_history(settings.run_history_path, session)

    print(
        "import finished "
        f"scanned={report.scanned} "
        f"imported={report.imported} "
        f"updated={report.updated} "
        f"parse_errors={report.parse_errors} "
        f"skipped={report.skipped}"
    )


if __name__ == "__main__":
    main()
