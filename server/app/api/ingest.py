from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlmodel import Session

from app.db.session import get_session
from app.models.schemas import IngestBatchIn
from app.services.ingest import ingest_batch, resolve_project_by_api_key

router = APIRouter()


@router.post("/ingest")
def ingest(
    batch: IngestBatchIn,
    session: Session = Depends(get_session),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> dict:
    project = resolve_project_by_api_key(session, x_api_key)
    if project is None:
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key")
    return ingest_batch(session, batch, project)
