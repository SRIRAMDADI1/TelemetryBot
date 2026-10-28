"""TelemetryClient — batching, run/span context, flush."""

from __future__ import annotations

import logging
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from agentelemetry.config import TelemetryConfig, find_config, load_config
from agentelemetry import context as ctx
from agentelemetry.pricing import estimate_cost_usd
from agentelemetry.schemas import (
    Channel,
    HandoffEvent,
    IngestBatch,
    LLMCallEvent,
    RunEvent,
    RunStatus,
    SpanEvent,
    SpanStatus,
    ToolCallEvent,
    utcnow,
)
from agentelemetry.transports.http import HttpTransport

logger = logging.getLogger("agentelemetry")


class TelemetryClient:
    def __init__(self, config: TelemetryConfig, transport: HttpTransport | None = None) -> None:
        self.config = config
        self.transport = transport or HttpTransport(
            collector_url=config.collector_url,
            api_key=config.api_key,
            timeout_seconds=config.timeout_seconds,
        )
        self._lock = threading.Lock()
        self._batch = IngestBatch()
        self._enabled = config.enabled
        ctx.set_client(self)

    @classmethod
    def from_config(cls, path: str | Path) -> TelemetryClient:
        return cls(load_config(path))

    @classmethod
    def from_env(cls, start: Path | None = None) -> TelemetryClient | None:
        """Load nearest telemetry.yaml, or return None if missing/disabled."""
        path = find_config(start)
        if path is None:
            return None
        try:
            config = load_config(path)
        except Exception as exc:
            logger.warning("Could not load telemetry config %s: %s", path, exc)
            return None
        if not config.enabled:
            return None
        return cls(config)

    @property
    def project_id(self) -> str:
        return self.config.project_id

    def _enqueue(self, **kwargs: Any) -> None:
        if not self._enabled:
            return
        with self._lock:
            for key, values in kwargs.items():
                getattr(self._batch, key).extend(values if isinstance(values, list) else [values])

    def flush(self) -> dict[str, Any]:
        if not self._enabled:
            return {"ok": True, "skipped": True}
        with self._lock:
            batch = self._batch
            self._batch = IngestBatch()
        if not any([batch.runs, batch.spans, batch.llm_calls, batch.tool_calls, batch.handoffs]):
            return {"ok": True, "empty": True}
        return self.transport.send_batch(batch)

    @contextmanager
    def start_run(
        self,
        *,
        external_id: str | None = None,
        channel: Channel | str = Channel.CLI,
        experiment: str | None = None,
        metadata: dict[str, Any] | None = None,
        auto_flush: bool = True,
    ) -> Iterator[RunEvent]:
        channel_enum = Channel(channel) if isinstance(channel, str) else channel
        run = RunEvent(
            project_id=self.project_id,
            external_id=external_id,
            channel=channel_enum,
            experiment=experiment,
            metadata=metadata or {},
        )
        previous = ctx.get_run()
        ctx.set_run(run)
        self._enqueue(runs=run)
        try:
            yield run
            if run.status == RunStatus.RUNNING:
                run.status = RunStatus.SUCCEEDED
            run.ended_at = utcnow()
            self._enqueue(runs=run)
        except Exception as exc:
            run.status = RunStatus.FAILED
            run.outcome = "error"
            run.ended_at = utcnow()
            run.metadata = {**run.metadata, "error": str(exc)}
            self._enqueue(runs=run)
            raise
        finally:
            ctx.set_run(previous)
            if auto_flush:
                self.flush()

    def end_run(
        self,
        run: RunEvent | None = None,
        *,
        status: RunStatus | str = RunStatus.SUCCEEDED,
        outcome: str | None = None,
        flush: bool = True,
    ) -> RunEvent | None:
        active = run or ctx.get_run()
        if active is None:
            return None
        active.status = RunStatus(status) if isinstance(status, str) else status
        if outcome is not None:
            active.outcome = outcome
        active.ended_at = utcnow()
        self._enqueue(runs=active)
        if flush:
            self.flush()
        return active

    @contextmanager
    def span(
        self,
        agent_name: str,
        *,
        parent_span_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Iterator[SpanEvent]:
        run = ctx.get_run()
        if run is None:
            raise RuntimeError("No active run — call start_run() first")
        parent = parent_span_id
        if parent is None:
            current = ctx.get_span()
            parent = current.span_id if current else None
        event = SpanEvent(
            run_id=run.run_id,
            project_id=self.project_id,
            parent_span_id=parent,
            agent_name=agent_name,
            metadata=metadata or {},
        )
        previous = ctx.get_span()
        ctx.set_span(event)
        try:
            yield event
            if event.status != SpanStatus.ERROR:
                event.status = SpanStatus.OK
            event.ended_at = utcnow()
        except Exception as exc:
            event.status = SpanStatus.ERROR
            event.error = str(exc)
            event.ended_at = utcnow()
            raise
        finally:
            self._enqueue(spans=event)
            ctx.set_span(previous)

    def record_llm_call(
        self,
        *,
        agent_name: str,
        model: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_tokens: int = 0,
        latency_ms: int = 0,
        finish_reason: str | None = None,
        span_id: str | None = None,
        run_id: str | None = None,
    ) -> LLMCallEvent | None:
        run = ctx.get_run()
        span = ctx.get_span()
        rid = run_id or (run.run_id if run else None)
        sid = span_id or (span.span_id if span else None)
        if rid is None or sid is None:
            logger.debug("Skipping LLM call — no active run/span")
            return None
        total = total_tokens or (prompt_tokens + completion_tokens)
        event = LLMCallEvent(
            span_id=sid,
            run_id=rid,
            project_id=self.project_id,
            agent_name=agent_name,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total,
            latency_ms=latency_ms,
            cost_usd=estimate_cost_usd(model, prompt_tokens, completion_tokens),
            finish_reason=finish_reason,
        )
        self._enqueue(llm_calls=event)
        return event

    def record_tool_call(
        self,
        *,
        agent_name: str,
        tool_name: str,
        latency_ms: int = 0,
        success: bool = True,
        args_hash: str | None = None,
        span_id: str | None = None,
        run_id: str | None = None,
    ) -> ToolCallEvent | None:
        run = ctx.get_run()
        span = ctx.get_span()
        rid = run_id or (run.run_id if run else None)
        sid = span_id or (span.span_id if span else None)
        if rid is None or sid is None:
            return None
        event = ToolCallEvent(
            span_id=sid,
            run_id=rid,
            project_id=self.project_id,
            agent_name=agent_name,
            tool_name=tool_name,
            latency_ms=latency_ms,
            success=success,
            args_hash=args_hash,
        )
        self._enqueue(tool_calls=event)
        return event

    def record_handoff(
        self,
        *,
        from_span_id: str,
        to_span_id: str,
        reason: str | None = None,
        run_id: str | None = None,
    ) -> HandoffEvent | None:
        run = ctx.get_run()
        rid = run_id or (run.run_id if run else None)
        if rid is None:
            return None
        event = HandoffEvent(
            run_id=rid,
            project_id=self.project_id,
            from_span_id=from_span_id,
            to_span_id=to_span_id,
            reason=reason,
        )
        self._enqueue(handoffs=event)
        return event
