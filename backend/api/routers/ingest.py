from __future__ import annotations

from fastapi import APIRouter

from api.schemas import IngestIssueResponse, IngestStatusResponse
from api.state import ingest_status


router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.get("/status", response_model=IngestStatusResponse)
def ingest_status_endpoint() -> IngestStatusResponse:
    return IngestStatusResponse(
        scanned=ingest_status.scanned,
        imported=ingest_status.imported,
        updated=ingest_status.updated,
        parse_errors=ingest_status.parse_errors,
        skipped=ingest_status.skipped,
        recent_issues=[
            IngestIssueResponse(
                kind=issue.kind,
                file_path=issue.file_path,
                message=issue.message,
                timestamp=issue.timestamp,
            )
            for issue in ingest_status.recent_issues
        ],
        last_processed_run_id=ingest_status.last_processed_run_id,
        last_processed_file=ingest_status.last_processed_file,
        last_event_at=ingest_status.last_event_at,
    )
