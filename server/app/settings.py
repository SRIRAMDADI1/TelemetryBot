from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env next to the server package root (…/server/.env), not cwd-dependent.
_SERVER_ROOT = Path(__file__).resolve().parents[1]
_ENV_FILE = _SERVER_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "sqlite:///./telemetrybot.db"
    seed_on_startup: bool = True

    # Public URLs (OAuth redirects + cookie scope)
    collector_public_url: str = "http://localhost:8100"
    dashboard_url: str = "http://localhost:3000"

    # Session
    session_ttl_hours: int = 168  # 7 days
    session_cookie_name: str = "tb_session"

    # Demo email account (always seeded; owns system projects)
    demo_email: str = "demo@telemetrybot.dev"
    demo_password: str = "demo"
    demo_name: str = "Demo User"

    # When true (default locally), GitHub sign-in works without a real OAuth app
    auth_dev_mode: bool = True

    # GitHub OAuth (optional — real flow when both set)
    github_client_id: str = ""
    github_client_secret: str = ""

    @field_validator("collector_public_url", "dashboard_url")
    @classmethod
    def _rstrip_slash(cls, value: str) -> str:
        return value.rstrip("/")

    @property
    def github_enabled(self) -> bool:
        return bool(self.github_client_id and self.github_client_secret)


@lru_cache
def get_settings() -> Settings:
    # Process env vars still win over .env (pydantic-settings default).
    return Settings()


def clear_settings_cache() -> None:
    get_settings.cache_clear()
