"""Helpers for recording LLM usage onto the active span."""

from __future__ import annotations

import time
from typing import Any, Callable

from agentelemetry import context as ctx
from agentelemetry.client import TelemetryClient
from agentelemetry.pricing import estimate_cost_usd
from agentelemetry.schemas import LLMCallEvent


def _client() -> TelemetryClient | None:
    client = ctx.get_client()
    return client if isinstance(client, TelemetryClient) else None


def record_llm_usage(
    *,
    agent_name: str,
    model: str,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    total_tokens: int = 0,
    latency_ms: int = 0,
    finish_reason: str | None = None,
    tool_calls: int = 0,
) -> LLMCallEvent | None:
    """Record an LLM call from an existing usage object (e.g. sales-ivr LLMUsage)."""
    client = _client()
    if client is None:
        return None
    event = client.record_llm_call(
        agent_name=agent_name,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        latency_ms=latency_ms,
        finish_reason=finish_reason,
    )
    if event and tool_calls > 0:
        for i in range(tool_calls):
            client.record_tool_call(
                agent_name=agent_name,
                tool_name=f"tool_{i + 1}",
                success=True,
            )
    return event


def trace_llm_call(
    *,
    model: str,
    agent_name: str | None = None,
    call: Callable[[], Any] | None = None,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    total_tokens: int = 0,
    finish_reason: str | None = None,
) -> Any:
    """Either wrap a callable LLM invocation or record a completed call.

    If ``call`` is provided, measures latency around it and expects the return
    value to optionally expose ``.usage`` with token fields.
    """
    client = _client()
    span = ctx.get_span()
    name = agent_name or (span.agent_name if span else "unknown")

    if call is None:
        if client is None:
            return None
        return client.record_llm_call(
            agent_name=name,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            finish_reason=finish_reason,
        )

    started = time.perf_counter()
    result = call()
    latency_ms = int((time.perf_counter() - started) * 1000)
    usage = getattr(result, "usage", None)
    pt = prompt_tokens
    ct = completion_tokens
    tt = total_tokens
    fr = finish_reason
    mdl = model
    if usage is not None:
        pt = getattr(usage, "prompt_tokens", pt) or pt
        ct = getattr(usage, "completion_tokens", ct) or ct
        tt = getattr(usage, "total_tokens", tt) or tt
        fr = getattr(usage, "finish_reason", fr) or fr
        mdl = getattr(usage, "model", mdl) or mdl
    if client is not None:
        client.record_llm_call(
            agent_name=name,
            model=mdl,
            prompt_tokens=pt,
            completion_tokens=ct,
            total_tokens=tt or (pt + ct),
            latency_ms=latency_ms,
            finish_reason=fr,
        )
    return result


def cost_for_usage(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    return estimate_cost_usd(model, prompt_tokens, completion_tokens)
