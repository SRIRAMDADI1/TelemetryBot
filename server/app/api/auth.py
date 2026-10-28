from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, Field
from sqlmodel import Session

from app.api.deps import get_current_user_optional, require_user, session_token_from_request
from app.db.session import User, get_session
from app.services.auth import (
    consume_magic_link,
    consume_oauth_state,
    create_magic_link,
    create_oauth_state,
    create_session,
    find_user_by_email,
    get_user_by_session_token,
    public_user,
    revoke_session,
    upsert_email_user,
    upsert_oauth_user,
    verify_password,
)
from app.settings import get_settings

router = APIRouter()


class EmailLoginIn(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=1)


class EmailRegisterIn(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=4)
    name: str | None = None


class MagicRequestIn(BaseModel):
    email: str = Field(min_length=3)


class MagicVerifyIn(BaseModel):
    token: str


class DevOAuthIn(BaseModel):
    email: str | None = None
    name: str | None = None
    github_login: str | None = None


def _set_session_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=settings.session_ttl_hours * 3600,
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(settings.session_cookie_name, path="/")


def _auth_payload(user: User, token: str) -> dict[str, Any]:
    return {"ok": True, "session_token": token, "user": public_user(user)}


def _safe_dashboard_path(redirect_to: str | None, default: str = "/auth/callback") -> str:
    """Only allow same-app relative paths (block open redirects)."""
    dest = (redirect_to or default).strip() or default
    if not dest.startswith("/") or dest.startswith("//") or "://" in dest:
        return default
    return dest


def _no_store_redirect(url: str, status_code: int = 302) -> RedirectResponse:
    response = RedirectResponse(url, status_code=status_code)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    return response


def _dashboard_finish(token: str, redirect_to: str | None = None) -> RedirectResponse:
    settings = get_settings()
    dest = _safe_dashboard_path(redirect_to)
    base = f"{settings.dashboard_url}{dest}"
    sep = "&" if "?" in base else "?"
    return _no_store_redirect(f"{base}{sep}token={token}")


def _dev_confirm_page(*, continue_url: str, cancel_url: str) -> HTMLResponse:
    from html import escape

    label = "GitHub"
    continue_href = escape(continue_url, quote=True)
    cancel_href = escape(cancel_url, quote=True)
    html = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Continue with {label}</title>
    <style>
      body {{ margin:0; min-height:100vh; display:flex; align-items:center; justify-content:center;
        background:#08080a; color:#f4f4f6; font:16px/1.5 "Segoe UI", sans-serif; }}
      .card {{ width:min(26rem, calc(100% - 2rem)); border:1px solid #2a2a30; border-radius:16px; padding:2rem; }}
      h1 {{ margin:0; font-size:1.4rem; }}
      p {{ color:#8b8b95; }}
      .row {{ display:flex; gap:.75rem; margin-top:1.5rem; }}
      a {{ color:#08080a; background:#f4f4f6; text-decoration:none; border-radius:8px; padding:.7rem 1rem; font-size:.9rem; }}
      a.secondary {{ color:#f4f4f6; background:transparent; border:1px solid #2a2a30; }}
    </style>
  </head>
  <body>
    <div class="card">
      <h1>Continue with {label}?</h1>
      <p>Sign-in does not continue automatically. Confirm to use the local mock {label} account.</p>
      <div class="row">
        <a href="{continue_href}">Continue</a>
        <a class="secondary" href="{cancel_href}">Cancel</a>
      </div>
    </div>
  </body>
</html>"""
    return HTMLResponse(html, headers={"Cache-Control": "no-store"})


@router.get("/providers")
def providers() -> dict[str, Any]:
    settings = get_settings()
    return {
        "email": True,
        "magic_link": True,
        "github": settings.github_enabled or settings.auth_dev_mode,
        "github_real": settings.github_enabled,
        "dev_mode": settings.auth_dev_mode,
        "demo_email": settings.demo_email,
    }


@router.get("/me")
def me(user: User = Depends(require_user)) -> dict[str, Any]:
    return {"user": public_user(user)}


@router.post("/logout")
def logout(
    response: Response,
    session: Session = Depends(get_session),
    token: str | None = Depends(session_token_from_request),
) -> dict[str, bool]:
    revoke_session(session, token)
    _clear_session_cookie(response)
    return {"ok": True}


@router.post("/email/login")
def email_login(
    body: EmailLoginIn,
    response: Response,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    user = find_user_by_email(session, body.email)
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    auth = create_session(session, user)
    _set_session_cookie(response, auth.token)
    return _auth_payload(user, auth.token)


@router.post("/email/register")
def email_register(
    body: EmailRegisterIn,
    response: Response,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    existing = find_user_by_email(session, body.email)
    if existing and existing.password_hash:
        raise HTTPException(status_code=409, detail="Account already exists — sign in instead")
    user = upsert_email_user(
        session,
        email=str(body.email),
        name=body.name,
        password=body.password,
    )
    auth = create_session(session, user)
    _set_session_cookie(response, auth.token)
    return _auth_payload(user, auth.token)


@router.post("/email/magic")
def magic_request(body: MagicRequestIn, session: Session = Depends(get_session)) -> dict[str, Any]:
    """Send (or in dev, return) a magic login link for email."""
    settings = get_settings()
    link = create_magic_link(session, str(body.email))
    verify_url = f"{settings.dashboard_url}/login?magic={link.token}"
    payload: dict[str, Any] = {
        "ok": True,
        "message": "If that email can receive mail, a sign-in link was sent.",
    }
    # Always expose in auth_dev_mode so local demos work without SMTP
    if settings.auth_dev_mode:
        payload["dev_token"] = link.token
        payload["dev_url"] = verify_url
    return payload


@router.post("/email/magic/verify")
def magic_verify(
    body: MagicVerifyIn,
    response: Response,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    link = consume_magic_link(session, body.token)
    if link is None:
        raise HTTPException(status_code=400, detail="Invalid or expired magic link")
    user = upsert_email_user(session, email=link.email)
    auth = create_session(session, user)
    _set_session_cookie(response, auth.token)
    return _auth_payload(user, auth.token)


@router.get("/github/start")
def github_start(
    intent: str = Query(default="login"),
    redirect_to: str | None = Query(default=None),
    session_token: str | None = Query(default=None),
    session: Session = Depends(get_session),
    user: User | None = Depends(get_current_user_optional),
):
    settings = get_settings()
    if intent not in {"login", "connect"}:
        raise HTTPException(status_code=400, detail="intent must be login or connect")

    # Dashboard stores the session cookie on its own origin — allow token passthrough
    if user is None and session_token:
        user = get_user_by_session_token(session, session_token)

    if intent == "connect" and user is None:
        raise HTTPException(status_code=401, detail="Sign in before connecting GitHub")

    if not settings.github_enabled:
        # Mock GitHub login (any visitor) or mock connect (seeded demo account only).
        if settings.auth_dev_mode and intent == "login":
            q = urlencode({**( {"redirect_to": redirect_to} if redirect_to else {})})
            url = f"{settings.collector_public_url}/v1/auth/dev/github/login"
            if q:
                url += f"?{q}"
            return _no_store_redirect(url)
        if (
            settings.auth_dev_mode
            and intent == "connect"
            and user is not None
            and user.is_demo
        ):
            q = urlencode(
                {
                    "intent": intent,
                    **({"redirect_to": redirect_to} if redirect_to else {}),
                }
            )
            url = f"{settings.collector_public_url}/v1/auth/dev/github/redirect?{q}"
            st = create_oauth_state(
                session,
                provider="github",
                intent="connect",
                user_id=user.id,
                redirect_to=redirect_to,
            )
            url += f"&state={st.state}"
            return _no_store_redirect(url)
        raise HTTPException(status_code=501, detail="GitHub OAuth is not configured")

    st = create_oauth_state(
        session,
        provider="github",
        intent=intent,
        user_id=user.id if user else None,
        redirect_to=redirect_to,
    )
    scope = "read:user user:email" if intent == "login" else "read:user user:email repo"
    oauth_params = {
        "client_id": settings.github_client_id,
        "redirect_uri": f"{settings.collector_public_url}/v1/auth/github/callback",
        "scope": scope,
        "state": st.state,
        "allow_signup": "true",
    }
    # Interrupt GitHub's silent re-auth after a previous grant.
    if intent == "login":
        oauth_params["prompt"] = "select_account"
    params = urlencode(oauth_params)
    return _no_store_redirect(f"https://github.com/login/oauth/authorize?{params}")


@router.get("/github/callback")
def github_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    session: Session = Depends(get_session),
):
    settings = get_settings()
    if error:
        q = urlencode({"error": error})
        return _no_store_redirect(f"{settings.dashboard_url}/login?{q}")
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code/state")
    oauth_state = consume_oauth_state(session, state, "github")
    if oauth_state is None:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    token_resp = httpx.post(
        "https://github.com/login/oauth/access_token",
        headers={"Accept": "application/json"},
        data={
            "client_id": settings.github_client_id,
            "client_secret": settings.github_client_secret,
            "code": code,
            "redirect_uri": f"{settings.collector_public_url}/v1/auth/github/callback",
        },
        timeout=20.0,
    )
    if token_resp.status_code >= 400:
        raise HTTPException(status_code=400, detail="GitHub token exchange failed")
    access = token_resp.json().get("access_token")
    if not access:
        raise HTTPException(status_code=400, detail="GitHub did not return an access token")

    gh = httpx.Client(
        headers={
            "Authorization": f"Bearer {access}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        timeout=20.0,
    )
    profile = gh.get("https://api.github.com/user").json()
    emails = gh.get("https://api.github.com/user/emails").json()
    primary = next((e for e in emails if e.get("primary") and e.get("verified")), None)
    email = (primary or (emails[0] if emails else {})).get("email") or f"{profile['login']}@users.noreply.github.com"

    existing = None
    if oauth_state.intent == "connect" and oauth_state.user_id:
        existing = session.get(User, oauth_state.user_id)

    user = upsert_oauth_user(
        session,
        provider="github",
        subject=str(profile["id"]),
        email=email,
        name=profile.get("name") or profile.get("login") or email.split("@")[0],
        avatar_url=profile.get("avatar_url"),
        github_login=profile.get("login"),
        github_access_token=access,
        existing_user=existing,
    )
    auth = create_session(session, user)
    dest = oauth_state.redirect_to or ("/connect" if oauth_state.intent == "connect" else "/auth/callback")
    return _dashboard_finish(auth.token, dest)


@router.get("/dev/github/login")
def dev_github_login(
    redirect_to: str | None = Query(default=None),
    confirm: bool = Query(default=False),
    session: Session = Depends(get_session),
):
    """Stable mock GitHub user for local login when AUTH_DEV_MODE is on."""
    settings = get_settings()
    if not settings.auth_dev_mode:
        raise HTTPException(status_code=404, detail="Not found")
    if not confirm:
        q = urlencode(
            {
                "confirm": "1",
                **({"redirect_to": redirect_to} if redirect_to else {}),
            }
        )
        return _dev_confirm_page(
            continue_url=f"{settings.collector_public_url}/v1/auth/dev/github/login?{q}",
            cancel_url=f"{settings.dashboard_url}/login",
        )
    user = upsert_oauth_user(
        session,
        provider="github",
        subject="dev-github-login",
        email="github-dev@telemetrybot.dev",
        name="GitHub Dev User",
        github_login="github-dev",
        github_access_token="dev-github-token",
    )
    auth = create_session(session, user)
    return _dashboard_finish(auth.token, redirect_to)


@router.get("/dev/github/redirect")
def dev_github_redirect(
    intent: str = Query(default="login"),
    redirect_to: str | None = Query(default=None),
    state: str | None = Query(default=None),
    session: Session = Depends(get_session),
):
    settings = get_settings()
    if not settings.auth_dev_mode:
        raise HTTPException(status_code=404, detail="Not found")

    existing = None
    dest = redirect_to
    if state:
        oauth_state = consume_oauth_state(session, state, "github")
        if oauth_state:
            intent = oauth_state.intent
            dest = oauth_state.redirect_to or dest
            if oauth_state.user_id:
                existing = session.get(User, oauth_state.user_id)

    # Only the seeded demo account may use the mock connect identity.
    if intent != "connect" or existing is None or not existing.is_demo:
        raise HTTPException(status_code=501, detail="GitHub OAuth is not configured")

    login = "octocat-dev"
    user = upsert_oauth_user(
        session,
        provider="github",
        subject="dev-github-stable",
        email=existing.email,
        name=existing.name or "Demo User",
        github_login=login,
        github_access_token="dev-github-token",
        existing_user=existing,
    )
    auth = create_session(session, user)
    dest = dest or "/connect"
    return _dashboard_finish(auth.token, dest)


@router.post("/dev/github")
def dev_github(
    body: DevOAuthIn,
    response: Response,
    session: Session = Depends(get_session),
    current: User | None = Depends(get_current_user_optional),
) -> dict[str, Any]:
    settings = get_settings()
    if not settings.auth_dev_mode:
        raise HTTPException(status_code=404, detail="Not found")
    if current is None or not current.is_demo:
        raise HTTPException(status_code=501, detail="GitHub OAuth is not configured")
    user = upsert_oauth_user(
        session,
        provider="github",
        subject="dev-github-stable",
        email=current.email,
        name=body.name or current.name or "Demo User",
        github_login=body.github_login or "octocat-dev",
        github_access_token="dev-github-token",
        existing_user=current,
    )
    auth = create_session(session, user)
    _set_session_cookie(response, auth.token)
    return _auth_payload(user, auth.token)
