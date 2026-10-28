from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.api.deps import require_user
from app.db.session import Project, User, get_session
from app.services.metrics import agent_stats
from app.services.seed import user_can_access_project

router = APIRouter()


@router.get("/agents/stats")
def stats(
    project_id: str = Query(...),
    limit_runs: int = Query(100, ge=1, le=500),
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
) -> dict:
    project = session.get(Project, project_id) or session.exec(
        select(Project).where(Project.slug == project_id)
    ).first()
    if project is None or not user_can_access_project(user, project):
        raise HTTPException(status_code=404, detail="Project not found")
    return {
        "project_id": project_id,
        "agents": agent_stats(session, project_id, limit_runs),
    }
