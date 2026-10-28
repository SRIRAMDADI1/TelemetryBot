from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, timezone

from sqlalchemy import Column, JSON, text
from sqlmodel import Field, Session, SQLModel, create_engine

from app.settings import get_settings


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: str = Field(primary_key=True)
    email: str = Field(index=True, unique=True)
    name: str = ""
    avatar_url: str | None = None
    password_hash: str | None = None
    github_id: str | None = Field(default=None, index=True)
    github_login: str | None = None
    github_access_token: str | None = None
    is_demo: bool = False
    created_at: datetime = Field(default_factory=utcnow)


class AuthSession(SQLModel, table=True):
    __tablename__ = "auth_sessions"

    token: str = Field(primary_key=True)
    user_id: str = Field(index=True)
    expires_at: datetime = Field(index=True)
    created_at: datetime = Field(default_factory=utcnow)
    # pending OAuth state payloads (login vs connect, nonce)
    label: str | None = None


class OAuthState(SQLModel, table=True):
    """Short-lived OAuth CSRF state."""

    __tablename__ = "oauth_states"

    state: str = Field(primary_key=True)
    provider: str
    intent: str = "login"  # login | connect
    user_id: str | None = None  # set when connecting GitHub to an existing session
    redirect_to: str | None = None
    expires_at: datetime = Field(index=True)
    created_at: datetime = Field(default_factory=utcnow)


class MagicLink(SQLModel, table=True):
    __tablename__ = "magic_links"

    token: str = Field(primary_key=True)
    email: str = Field(index=True)
    expires_at: datetime = Field(index=True)
    created_at: datetime = Field(default_factory=utcnow)
    consumed: bool = False


class Project(SQLModel, table=True):
    id: str = Field(primary_key=True)
    slug: str = Field(index=True, unique=True)
    name: str
    repo_url: str | None = None
    local_path: str | None = None
    ingest_api_key: str = Field(index=True)
    is_system: bool = False
    owner_id: str | None = Field(default=None, index=True)
    github_full_name: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
    coverage_json: dict | None = Field(default=None, sa_column=Column(JSON))


class RunRow(SQLModel, table=True):
    __tablename__ = "runs"

    run_id: str = Field(primary_key=True)
    project_id: str = Field(index=True)
    external_id: str | None = Field(default=None, index=True)
    status: str = "running"
    channel: str = "cli"
    outcome: str | None = None
    experiment: str | None = Field(default=None, index=True)
    started_at: datetime = Field(default_factory=utcnow, index=True)
    ended_at: datetime | None = None
    metadata_json: dict | None = Field(default=None, sa_column=Column(JSON))
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    span_count: int = 0
    duration_ms: int = 0


class SpanRow(SQLModel, table=True):
    __tablename__ = "spans"

    span_id: str = Field(primary_key=True)
    run_id: str = Field(index=True)
    project_id: str = Field(index=True)
    parent_span_id: str | None = None
    agent_name: str = Field(index=True)
    status: str = "ok"
    started_at: datetime = Field(default_factory=utcnow)
    ended_at: datetime | None = None
    error: str | None = None
    metadata_json: dict | None = Field(default=None, sa_column=Column(JSON))
    latency_ms: int = 0


class LLMCallRow(SQLModel, table=True):
    __tablename__ = "llm_calls"

    call_id: str = Field(primary_key=True)
    span_id: str = Field(index=True)
    run_id: str = Field(index=True)
    project_id: str = Field(index=True)
    agent_name: str = Field(index=True)
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: int = 0
    cost_usd: float = 0.0
    finish_reason: str | None = None
    timestamp: datetime = Field(default_factory=utcnow)


class ToolCallRow(SQLModel, table=True):
    __tablename__ = "tool_calls"

    tool_call_id: str = Field(primary_key=True)
    span_id: str = Field(index=True)
    run_id: str = Field(index=True)
    project_id: str = Field(index=True)
    agent_name: str
    tool_name: str
    latency_ms: int = 0
    success: bool = True
    args_hash: str | None = None
    timestamp: datetime = Field(default_factory=utcnow)


class HandoffRow(SQLModel, table=True):
    __tablename__ = "handoffs"

    handoff_id: str = Field(primary_key=True)
    run_id: str = Field(index=True)
    project_id: str = Field(index=True)
    from_span_id: str
    to_span_id: str
    reason: str | None = None
    timestamp: datetime = Field(default_factory=utcnow)


_engine = None


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        url = settings.database_url
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        _engine = create_engine(url, echo=False, connect_args=connect_args)
    return _engine


def init_db() -> None:
    SQLModel.metadata.create_all(get_engine())
    _migrate_sqlite_columns()


def _migrate_sqlite_columns() -> None:
    """Add columns introduced in F2 on existing SQLite DBs."""
    engine = get_engine()
    url = str(engine.url)
    if not url.startswith("sqlite"):
        return
    with engine.connect() as conn:
        rows = conn.execute(text("PRAGMA table_info(project)")).fetchall()
        cols = {r[1] for r in rows}
        alters: list[str] = []
        if "owner_id" not in cols:
            alters.append("ALTER TABLE project ADD COLUMN owner_id VARCHAR")
        if "github_full_name" not in cols:
            alters.append("ALTER TABLE project ADD COLUMN github_full_name VARCHAR")
        for stmt in alters:
            conn.execute(text(stmt))
        if alters:
            conn.commit()


def reset_engine() -> None:
    global _engine
    if _engine is not None:
        _engine.dispose()
    _engine = None


def get_session() -> Generator[Session, None, None]:
    with Session(get_engine()) as session:
        yield session
