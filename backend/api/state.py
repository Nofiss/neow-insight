from __future__ import annotations

from dataclasses import dataclass, field

from core.ingestion.importer import ImportIssue, ImportReport


@dataclass
class IngestStatus:
    scanned: int = 0
    imported: int = 0
    updated: int = 0
    parse_errors: int = 0
    skipped: int = 0
    recent_issues: list[ImportIssue] = field(default_factory=list)
    last_processed_run_id: str | None = None
    last_processed_file: str | None = None
    last_event_at: str | None = None


ingest_status = IngestStatus()


def apply_import_report(report: ImportReport) -> None:
    ingest_status.scanned = report.scanned
    ingest_status.imported = report.imported
    ingest_status.updated = report.updated
    ingest_status.parse_errors = report.parse_errors
    ingest_status.skipped = report.skipped
    ingest_status.recent_issues = list(report.recent_issues)
    ingest_status.last_processed_run_id = report.last_processed_run_id
    ingest_status.last_processed_file = report.last_processed_file
    ingest_status.last_event_at = report.last_event_at
