from __future__ import annotations

from dataclasses import dataclass

from core.ingestion.importer import ImportReport


@dataclass
class IngestStatus:
    scanned: int = 0
    imported: int = 0
    updated: int = 0
    parse_errors: int = 0
    skipped: int = 0


ingest_status = IngestStatus()


def apply_import_report(report: ImportReport) -> None:
    ingest_status.scanned = report.scanned
    ingest_status.imported = report.imported
    ingest_status.updated = report.updated
    ingest_status.parse_errors = report.parse_errors
    ingest_status.skipped = report.skipped
