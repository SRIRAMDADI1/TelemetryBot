from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlmodel import Session, select

from app.db.session import AuthSession, MagicLink, OAuthState, User, utcnow
from app.settings import get_settings


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
    return f"pbkdf2${salt}${digest.hex()}"


def verify_password(password: str, stored: str | None) -> bool:
    if not stored or not stored.startswith("pbkdf2$"):
        return False
    _, salt, expected = stored.split("$", 2)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
    return hmac.compare_digest(digest.hex(), expected)


def public_user(user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "avatar_url": user.avatar_url,
        "is_demo": user.is_demo,
        "github_connected": bool(user.github_id or user.github_access_token),
        "github_login": user.github_login,
        "has_password": bool(user.password_hash),
    }


def new_user_id() -> str:
    return f"usr_{secrets.token_urlsafe(12)}"


def create_session(session: Session, user: User) -> AuthSession:
    settings = get_settings()
    row = AuthSession(
        token=secrets.token_urlsafe(32),
        user_id=user.id,
        expires_at=utcnow() + timedelta(hours=settings.session_ttl_hours),
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_user_by_session_token(session: Session, token: str | None) -> User | None:
    if not token:
        return None
    row = session.get(AuthSession, token)
    if row is None:
        return None
    expires = row.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < utcnow():
        session.delete(row)
        session.commit()
        return None
    return session.get(User, row.user_id)


def revoke_session(session: Session, token: str | None) -> None:
    if not token:
        return
    row = session.get(AuthSession, token)
    if row:
        session.delete(row)
        session.commit()


def find_user_by_email(session: Session, email: str) -> User | None:
    return session.exec(select(User).where(User.email == email.lower().strip())).first()


def upsert_email_user(
    session: Session,
    *,
    email: str,
    name: str | None = None,
    password: str | None = None,
    is_demo: bool = False,
) -> User:
    email_norm = email.lower().strip()
    user = find_user_by_email(session, email_norm)
    if user is None:
        user = User(
            id=new_user_id(),
            email=email_norm,
            name=name or email_norm.split("@")[0],
            is_demo=is_demo,
        )
        if password:
            user.password_hash = hash_password(password)
        session.add(user)
    else:
        if name:
            user.name = name
        if password:
            user.password_hash = hash_password(password)
        if is_demo:
            user.is_demo = True
        session.add(user)
    session.commit()
    session.refresh(user)
    return user


def upsert_oauth_user(
    session: Session,
    *,
    provider: str,
    subject: str,
    email: str,
    name: str,
    avatar_url: str | None = None,
    github_login: str | None = None,
    github_access_token: str | None = None,
    existing_user: User | None = None,
) -> User:
    email_norm = email.lower().strip()
    user = existing_user

    if user is None:
        if provider == "github":
            user = session.exec(select(User).where(User.github_id == subject)).first()

    if user is None:
        user = find_user_by_email(session, email_norm)

    if user is None:
        user = User(id=new_user_id(), email=email_norm, name=name or email_norm.split("@")[0])
        session.add(user)

    user.email = email_norm or user.email
    user.name = name or user.name
    if avatar_url:
        user.avatar_url = avatar_url

    if provider == "github":
        user.github_id = subject
        user.github_login = github_login or user.github_login
        if github_access_token:
            user.github_access_token = github_access_token

    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def create_oauth_state(
    session: Session,
    *,
    provider: str,
    intent: str = "login",
    user_id: str | None = None,
    redirect_to: str | None = None,
    ttl_minutes: int = 15,
) -> OAuthState:
    row = OAuthState(
        state=secrets.token_urlsafe(24),
        provider=provider,
        intent=intent,
        user_id=user_id,
        redirect_to=redirect_to,
        expires_at=utcnow() + timedelta(minutes=ttl_minutes),
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def consume_oauth_state(session: Session, state: str, provider: str) -> OAuthState | None:
    row = session.get(OAuthState, state)
    if row is None or row.provider != provider:
        return None
    expires = row.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    session.delete(row)
    session.commit()
    if expires < utcnow():
        return None
    return row


def create_magic_link(session: Session, email: str, ttl_minutes: int = 30) -> MagicLink:
    row = MagicLink(
        token=secrets.token_urlsafe(24),
        email=email.lower().strip(),
        expires_at=utcnow() + timedelta(minutes=ttl_minutes),
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def consume_magic_link(session: Session, token: str) -> MagicLink | None:
    row = session.get(MagicLink, token)
    if row is None or row.consumed:
        return None
    expires = row.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < utcnow():
        return None
    row.consumed = True
    session.add(row)
    session.commit()
    return row
