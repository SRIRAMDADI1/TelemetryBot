from __future__ import annotations

from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.api.deps import require_user
from app.db.session import User, get_session
from app.settings import get_settings

router = APIRouter()

# Shown when AUTH_DEV_MODE and no real GitHub token — enough to demo “connect repo”
DEV_REPOS = [
    {
        "id": 1,
        "full_name": "example/sales-ivr",
        "name": "sales-ivr",
        "private": False,
        "html_url": "https://github.com/example/sales-ivr",
        "description": "Sales IVR multi-agent workload (demo)",
        "default_branch": "main",
    },
    {
        "id": 2,
        "full_name": "example/ado-pipeline",
        "name": "ado-pipeline",
        "private": False,
        "html_url": "https://github.com/example/ado-pipeline",
        "description": "ADO pipeline meta-agents (demo)",
        "default_branch": "main",
    },
    {
        "id": 3,
        "full_name": "octocat-dev/widget-agents",
        "name": "widget-agents",
        "private": True,
        "html_url": "https://github.com/octocat-dev/widget-agents",
        "description": "Sample private agent repo for connect-flow demos",
        "default_branch": "main",
    },
    {
        "id": 4,
        "full_name": "octocat-dev/support-bots",
        "name": "support-bots",
        "private": False,
        "html_url": "https://github.com/octocat-dev/support-bots",
        "description": "Customer support agent fleet",
        "default_branch": "main",
    },
]


@router.get("/github/status")
def github_status(user: User = Depends(require_user)) -> dict[str, Any]:
    settings = get_settings()
    connected = bool(user.github_id or user.github_access_token)
    return {
        "connected": connected,
        "login": user.github_login,
        "dev_mode": settings.auth_dev_mode and (user.github_access_token == "dev-github-token" or not settings.github_enabled),
        "oauth_configured": settings.github_enabled,
    }


@router.get("/github/repos")
def list_repos(
    per_page: int = Query(30, ge=1, le=100),
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    _ = session
    settings = get_settings()
    if not (user.github_id or user.github_access_token):
        raise HTTPException(status_code=400, detail="GitHub is not connected for this account")

    token = user.github_access_token
    if not token or token == "dev-github-token" or (settings.auth_dev_mode and not settings.github_enabled):
        return {"repos": DEV_REPOS, "source": "dev"}

    try:
        resp = httpx.get(
            "https://api.github.com/user/repos",
            params={"per_page": per_page, "sort": "updated", "affiliation": "owner,collaborator,organization_member"},
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=20.0,
        )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"GitHub unreachable: {exc}") from exc

    if resp.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"GitHub API error ({resp.status_code})")

    repos = []
    for r in resp.json():
        repos.append(
            {
                "id": r.get("id"),
                "full_name": r.get("full_name"),
                "name": r.get("name"),
                "private": r.get("private"),
                "html_url": r.get("html_url"),
                "description": r.get("description"),
                "default_branch": r.get("default_branch"),
            }
        )
    return {"repos": repos, "source": "github"}
