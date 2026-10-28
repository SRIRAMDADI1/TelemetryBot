from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.api.deps import require_user
from app.db.session import Project, RunRow, User, get_session
from app.services.metrics import compare_runs, efficiency_metrics
from app.services.seed import user_can_access_project

router = APIRouter()


@router.get("/metrics/efficiency")
def efficiency(
    project_id: str = Query(...),
    limit_runs: int = Query(200, ge=1, le=1000),
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
) -> dict:
    project = session.get(Project, project_id) or session.exec(
        select(Project).where(Project.slug == project_id)
    ).first()
    if project is None or not user_can_access_project(user, project):
        raise HTTPException(status_code=404, detail="Project not found")
    return efficiency_metrics(session, project_id, limit_runs)


@router.get("/metrics/compare")
def compare(
    run_a: str = Query(...),
    run_b: str = Query(...),
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
) -> dict:
    for run_id in (run_a, run_b):
        run = session.get(RunRow, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
        project = session.get(Project, run.project_id)
        if project is None or not user_can_access_project(user, project):
            raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    result = compare_runs(session, run_a, run_b)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
