from __future__ import annotations

from fastapi import Cookie, Depends, Header, HTTPException, Request
from sqlmodel import Session

from app.db.session import User, get_session
from app.services.auth import get_user_by_session_token
from app.settings import get_settings


def _extract_token(
    request: Request,
    authorization: str | None,
    cookie_token: str | None,
) -> str | None:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    settings = get_settings()
    if cookie_token:
        return cookie_token
    # Also accept raw cookie header in case alias differs
    return request.cookies.get(settings.session_cookie_name)


def get_current_user_optional(
    request: Request,
    session: Session = Depends(get_session),
    authorization: str | None = Header(default=None),
    tb_session: str | None = Cookie(default=None, alias="tb_session"),
) -> User | None:
    token = _extract_token(request, authorization, tb_session)
    return get_user_by_session_token(session, token)


def require_user(user: User | None = Depends(get_current_user_optional)) -> User:
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def session_token_from_request(
    request: Request,
    authorization: str | None = Header(default=None),
    tb_session: str | None = Cookie(default=None, alias="tb_session"),
) -> str | None:
    return _extract_token(request, authorization, tb_session)
