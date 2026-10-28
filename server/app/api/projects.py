from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.api.deps import require_user
from app.db.session import (
    HandoffRow,
    LLMCallRow,
    Project,
    RunRow,
    SpanRow,
    ToolCallRow,
    User,
    get_session,
)
from app.models.schemas import CoverageReport, ProjectCreate, ProjectFromGitHub
from app.services.seed import new_api_key, projects_for_user, user_can_access_project

router = APIRouter()


def _public_project(p: Project, *, reveal_key: bool = False) -> dict:
    key = p.ingest_api_key
    masked = (key[:4] + "…" + key[-4:]) if key and len(key) > 8 else "••••"
    return {
        "id": p.id,
        "slug": p.slug,
        "name": p.name,
        "repo_url": p.repo_url,
        "local_path": p.local_path,
        "is_system": p.is_system,
        "owner_id": p.owner_id,
        "github_full_name": p.github_full_name,
        "created_at": p.created_at,
        "ingest_api_key_masked": masked,
        "ingest_api_key": key if reveal_key else None,
        "coverage": p.coverage_json,
    }


def _get_project(session: Session, project_ref: str) -> Project | None:
    project = session.get(Project, project_ref)
    if project is None:
        project = session.exec(select(Project).where(Project.slug == project_ref)).first()
    return project


def _require_project_access(session: Session, user: User, project_ref: str) -> Project:
    project = _get_project(session, project_ref)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if not user_can_access_project(user, project):
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _delete_project_telemetry(session: Session, project_id: str) -> None:
    for model in (HandoffRow, ToolCallRow, LLMCallRow, SpanRow, RunRow):
        for row in session.exec(select(model).where(model.project_id == project_id)).all():
            session.delete(row)


@router.get("/projects")
def list_projects(
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
) -> list[dict]:
    return [_public_project(p) for p in projects_for_user(session, user)]


@router.post("/projects")
def create_project(
    body: ProjectCreate,
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
) -> dict:
    existing = session.exec(select(Project).where(Project.slug == body.slug)).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Project slug '{body.slug}' exists")
    project_id = body.id or body.slug
    api_key = body.ingest_api_key or new_api_key()
    project = Project(
        id=project_id,
        slug=body.slug,
        name=body.name,
        repo_url=body.repo_url,
        local_path=body.local_path,
        ingest_api_key=api_key,
        is_system=body.is_system,
        owner_id=user.id,
        github_full_name=body.github_full_name,
    )
    session.add(project)
    session.commit()
    session.refresh(project)
    return _public_project(project, reveal_key=True)


@router.post("/projects/from-github")
def create_from_github(
    body: ProjectFromGitHub,
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
) -> dict:
    if not (user.github_id or user.github_access_token):
        raise HTTPException(status_code=400, detail="Connect GitHub before importing a repo")

    full_name = body.full_name.strip().strip("/")
    if "/" not in full_name:
        raise HTTPException(status_code=400, detail="full_name must look like owner/repo")

    _owner, repo = full_name.split("/", 1)
    slug_base = body.slug or repo.lower().replace("_", "-")
    slug = slug_base
    n = 2
    while session.exec(select(Project).where(Project.slug == slug)).first():
        slug = f"{slug_base}-{n}"
        n += 1

    project = Project(
        id=slug,
        slug=slug,
        name=body.name or repo.replace("-", " ").replace("_", " ").title(),
        repo_url=body.html_url or f"https://github.com/{full_name}",
        local_path=None,
        ingest_api_key=new_api_key(),
        is_system=False,
        owner_id=user.id,
        github_full_name=full_name,
    )
    session.add(project)
    session.commit()
    session.refresh(project)
    return _public_project(project, reveal_key=True)


@router.get("/projects/{project_ref}")
def get_project(
    project_ref: str,
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
) -> dict:
    project = _require_project_access(session, user, project_ref)
    return _public_project(project)


@router.delete("/projects/{project_ref}")
def disconnect_project(
    project_ref: str,
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
) -> dict:
    """Remove a monitoring tab and its stored runs for the signed-in owner."""
    project = _require_project_access(session, user, project_ref)
    if project.is_system:
        raise HTTPException(
            status_code=403,
            detail="System demo projects can’t be disconnected",
        )
    if project.owner_id and project.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Only the project owner can disconnect it")

    slug = project.slug
    _delete_project_telemetry(session, project.id)
    session.delete(project)
    session.commit()
    return {"ok": True, "slug": slug}


@router.post("/projects/{project_ref}/coverage")
def set_coverage(
    project_ref: str,
    body: CoverageReport,
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
) -> dict:
    project = _require_project_access(session, user, project_ref)
    payload = body.model_dump(mode="json")
    if body.scanned_at is None:
        payload["scanned_at"] = datetime.now(timezone.utc).isoformat()
    project.coverage_json = payload
    session.add(project)
    session.commit()
    return _public_project(project)
