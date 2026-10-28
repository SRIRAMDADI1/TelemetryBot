"""Load telemetry.yaml configuration."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


_ENV_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def _expand_env(value: str) -> str:
    def repl(match: re.Match[str]) -> str:
        return os.environ.get(match.group(1), "")

    return _ENV_PATTERN.sub(repl, value)


def _expand_obj(obj: Any) -> Any:
    if isinstance(obj, str):
        return _expand_env(obj)
    if isinstance(obj, dict):
        return {k: _expand_obj(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_expand_obj(v) for v in obj]
    return obj


class TelemetryConfig(BaseModel):
    collector_url: str = "http://localhost:8100"
    project_id: str
    project_slug: str | None = None
    api_key: str = ""
    enabled: bool = True
    flush_interval_seconds: float = 2.0
    timeout_seconds: float = 5.0
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def slug(self) -> str:
        return self.project_slug or self.project_id


def load_config(path: str | Path) -> TelemetryConfig:
    config_path = Path(path)
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"Invalid telemetry config at {config_path}")
    return TelemetryConfig.model_validate(_expand_obj(raw))


def find_config(start: Path | None = None) -> Path | None:
    """Walk upward from start (or cwd) looking for telemetry.yaml."""
    cur = (start or Path.cwd()).resolve()
    for directory in [cur, *cur.parents]:
        candidate = directory / "telemetry.yaml"
        if candidate.is_file():
            return candidate
        if (directory / ".git").exists():
            break
    return None
