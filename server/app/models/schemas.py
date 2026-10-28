from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RunIn(BaseModel):
    run_id: str
    project_id: str
    external_id: str | None = None
    status: str = "running"
    channel: str = "cli"
    outcome: str | None = None
    experiment: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SpanIn(BaseModel):
    span_id: str
    run_id: str
    project_id: str
    parent_span_id: str | None = None
    agent_name: str
    status: str = "ok"
    started_at: datetime | None = None
    ended_at: datetime | None = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class LLMCallIn(BaseModel):
    call_id: str
    span_id: str
    run_id: str
    project_id: str
    agent_name: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: int = 0
    cost_usd: float = 0.0
    finish_reason: str | None = None
    timestamp: datetime | None = None


class ToolCallIn(BaseModel):
    tool_call_id: str
    span_id: str
    run_id: str
    project_id: str
    agent_name: str
    tool_name: str
    latency_ms: int = 0
    success: bool = True
    args_hash: str | None = None
    timestamp: datetime | None = None


class HandoffIn(BaseModel):
    handoff_id: str
    run_id: str
    project_id: str
    from_span_id: str
    to_span_id: str
    reason: str | None = None
    timestamp: datetime | None = None


class IngestBatchIn(BaseModel):
    runs: list[RunIn] = Field(default_factory=list)
    spans: list[SpanIn] = Field(default_factory=list)
    llm_calls: list[LLMCallIn] = Field(default_factory=list)
    tool_calls: list[ToolCallIn] = Field(default_factory=list)
    handoffs: list[HandoffIn] = Field(default_factory=list)


class ProjectCreate(BaseModel):
    id: str | None = None
    slug: str
    name: str
    repo_url: str | None = None
    local_path: str | None = None
    ingest_api_key: str | None = None
    is_system: bool = False
    github_full_name: str | None = None


class ProjectFromGitHub(BaseModel):
    full_name: str
    name: str | None = None
    slug: str | None = None
    html_url: str | None = None


class CoverageReport(BaseModel):
    scanned_at: datetime | None = None
    files_scanned: int = 0
    instrumented: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    notes: str | None = None
