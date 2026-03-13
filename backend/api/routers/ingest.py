from __future__ import annotations

from fastapi import APIRouter

from api.schemas import IngestStatusResponse
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
    )
