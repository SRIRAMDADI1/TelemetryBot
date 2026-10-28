"""Decorators for agent and tool tracing."""

from __future__ import annotations

import functools
from typing import Any, Callable, TypeVar

from agentelemetry import context as ctx
from agentelemetry.client import TelemetryClient

F = TypeVar("F", bound=Callable[..., Any])


def _client() -> TelemetryClient | None:
    client = ctx.get_client()
    return client if isinstance(client, TelemetryClient) else None


def trace_agent(name: str) -> Callable[[F], F]:
    """Wrap a function as an agent span under the active run."""

    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            client = _client()
            if client is None or ctx.get_run() is None:
                return fn(*args, **kwargs)
            with client.span(name):
                return fn(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator


def trace_tool(tool_name: str) -> Callable[[F], F]:
    """Wrap a tool function and record a ToolCallEvent."""

    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            import time

            client = _client()
            run = ctx.get_run()
            span = ctx.get_span()
            if client is None or run is None or span is None:
                return fn(*args, **kwargs)
            started = time.perf_counter()
            success = True
            try:
                return fn(*args, **kwargs)
            except Exception:
                success = False
                raise
            finally:
                latency_ms = int((time.perf_counter() - started) * 1000)
                client.record_tool_call(
                    agent_name=span.agent_name,
                    tool_name=tool_name,
                    latency_ms=latency_ms,
                    success=success,
                )

        return wrapper  # type: ignore[return-value]

    return decorator
