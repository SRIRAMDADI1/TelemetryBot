from __future__ import annotations

from sqlmodel import Session, select

from app.db.session import Project, get_engine
from app.services.auth import upsert_email_user
from app.settings import get_settings

SYSTEM_PROJECTS = [
    {
        "id": "sales-ivr",
        "slug": "sales-ivr",
        "name": "Sales IVR",
        "local_path": "./sales-ivr",
        "ingest_api_key": "dev-sales-ivr-key",
        "is_system": True,
        "repo_url": "https://github.com/example/sales-ivr",
        "github_full_name": "example/sales-ivr",
    },
    {
        "id": "ado-pipeline",
        "slug": "ado-pipeline",
        "name": "ADO Pipeline",
        "local_path": "./ado-pipeline",
        "ingest_api_key": "dev-ado-pipeline-key",
        "is_system": True,
        "repo_url": "https://github.com/example/ado-pipeline",
        "github_full_name": "example/ado-pipeline",
    },
]


def seed_system_projects() -> None:
    if not get_settings().seed_on_startup:
        return
    settings = get_settings()
    with Session(get_engine()) as session:
        demo = upsert_email_user(
            session,
            email=settings.demo_email,
            name=settings.demo_name,
            password=settings.demo_password,
            is_demo=True,
        )
        for item in SYSTEM_PROJECTS:
            existing = session.get(Project, item["id"])
            if existing is None:
                session.add(
                    Project(
                        **item,
                        owner_id=demo.id,
                    )
                )
            else:
                existing.name = item["name"]
                existing.local_path = item["local_path"]
                existing.is_system = True
                existing.repo_url = item.get("repo_url") or existing.repo_url
                existing.github_full_name = item.get("github_full_name") or existing.github_full_name
                if not existing.ingest_api_key:
                    existing.ingest_api_key = item["ingest_api_key"]
                if not existing.owner_id:
                    existing.owner_id = demo.id
                session.add(existing)
        session.commit()


def new_api_key() -> str:
    import secrets

    return f"tb_{secrets.token_urlsafe(24)}"


def user_can_access_project(user: User, project: Project) -> bool:
    if project.owner_id == user.id:
        return True
    # Demo user sees all system projects even if ownership drifted
    if user.is_demo and project.is_system:
        return True
    return False


def projects_for_user(session: Session, user: User) -> list[Project]:
    if user.is_demo:
        rows = session.exec(
            select(Project).where((Project.owner_id == user.id) | (Project.is_system == True))  # noqa: E712
        ).all()
    else:
        rows = session.exec(select(Project).where(Project.owner_id == user.id)).all()
    # Stable order: seeded system tabs in SYSTEM_PROJECTS order, then other projects by name.
    system_rank = {p["slug"]: i for i, p in enumerate(SYSTEM_PROJECTS)}
    return sorted(
        rows,
        key=lambda p: (
            0 if p.is_system else 1,
            system_rank.get(p.slug, 100),
            p.name.lower(),
        ),
    )
