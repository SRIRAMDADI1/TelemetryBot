"""Canonical telemetry event schemas."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid4())


class RunStatus(StrEnum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SpanStatus(StrEnum):
    OK = "ok"
    ERROR = "error"


class Channel(StrEnum):
    CLI = "cli"
    WEB = "web"
    BATCH = "batch"
    PIPELINE = "pipeline"
    DEMO = "demo"


class RunEvent(BaseModel):
    run_id: str = Field(default_factory=new_id)
    project_id: str
    external_id: str | None = None
    status: RunStatus = RunStatus.RUNNING
    channel: Channel = Channel.CLI
    outcome: str | None = None
    experiment: str | None = None
    started_at: datetime = Field(default_factory=utcnow)
    ended_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SpanEvent(BaseModel):
    span_id: str = Field(default_factory=new_id)
    run_id: str
    project_id: str
    parent_span_id: str | None = None
    agent_name: str
    status: SpanStatus = SpanStatus.OK
    started_at: datetime = Field(default_factory=utcnow)
    ended_at: datetime | None = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class LLMCallEvent(BaseModel):
    call_id: str = Field(default_factory=new_id)
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
    timestamp: datetime = Field(default_factory=utcnow)


class ToolCallEvent(BaseModel):
    tool_call_id: str = Field(default_factory=new_id)
    span_id: str
    run_id: str
    project_id: str
    agent_name: str
    tool_name: str
    latency_ms: int = 0
    success: bool = True
    args_hash: str | None = None
    timestamp: datetime = Field(default_factory=utcnow)


class HandoffEvent(BaseModel):
    handoff_id: str = Field(default_factory=new_id)
    run_id: str
    project_id: str
    from_span_id: str
    to_span_id: str
    reason: str | None = None
    timestamp: datetime = Field(default_factory=utcnow)


class IngestBatch(BaseModel):
    runs: list[RunEvent] = Field(default_factory=list)
    spans: list[SpanEvent] = Field(default_factory=list)
    llm_calls: list[LLMCallEvent] = Field(default_factory=list)
    tool_calls: list[ToolCallEvent] = Field(default_factory=list)
    handoffs: list[HandoffEvent] = Field(default_factory=list)
