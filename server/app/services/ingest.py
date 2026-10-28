from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Session, select

from app.db.session import (
    HandoffRow,
    LLMCallRow,
    Project,
    RunRow,
    SpanRow,
    ToolCallRow,
)
from app.models.schemas import IngestBatchIn


def resolve_project_by_api_key(session: Session, api_key: str | None) -> Project | None:
    if not api_key:
        return None
    return session.exec(select(Project).where(Project.ingest_api_key == api_key)).first()


def _duration_ms(started: datetime | None, ended: datetime | None) -> int:
    if not started or not ended:
        return 0
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    if ended.tzinfo is None:
        ended = ended.replace(tzinfo=timezone.utc)
    return max(0, int((ended - started).total_seconds() * 1000))


def ingest_batch(session: Session, batch: IngestBatchIn, project: Project) -> dict:
    run_ids: set[str] = set()

    for run in batch.runs:
        if run.project_id != project.id:
            continue
        row = session.get(RunRow, run.run_id)
        if row is None:
            row = RunRow(run_id=run.run_id, project_id=project.id)
            session.add(row)
        row.external_id = run.external_id
        row.status = run.status
        row.channel = run.channel
        row.outcome = run.outcome
        row.experiment = run.experiment
        if run.started_at:
            row.started_at = run.started_at
        row.ended_at = run.ended_at
        row.metadata_json = run.metadata
        row.duration_ms = _duration_ms(row.started_at, row.ended_at)
        run_ids.add(run.run_id)

    for span in batch.spans:
        if span.project_id != project.id:
            continue
        row = session.get(SpanRow, span.span_id)
        if row is None:
            row = SpanRow(span_id=span.span_id, run_id=span.run_id, project_id=project.id)
            session.add(row)
        row.parent_span_id = span.parent_span_id
        row.agent_name = span.agent_name
        row.status = span.status
        if span.started_at:
            row.started_at = span.started_at
        row.ended_at = span.ended_at
        row.error = span.error
        row.metadata_json = span.metadata
        row.latency_ms = _duration_ms(row.started_at, row.ended_at)
        run_ids.add(span.run_id)

    for call in batch.llm_calls:
        if call.project_id != project.id:
            continue
        row = session.get(LLMCallRow, call.call_id)
        if row is None:
            row = LLMCallRow(
                call_id=call.call_id,
                span_id=call.span_id,
                run_id=call.run_id,
                project_id=project.id,
                agent_name=call.agent_name,
                model=call.model,
            )
            session.add(row)
        row.prompt_tokens = call.prompt_tokens
        row.completion_tokens = call.completion_tokens
        row.total_tokens = call.total_tokens
        row.latency_ms = call.latency_ms
        row.cost_usd = call.cost_usd
        row.finish_reason = call.finish_reason
        if call.timestamp:
            row.timestamp = call.timestamp
        run_ids.add(call.run_id)

    for tool in batch.tool_calls:
        if tool.project_id != project.id:
            continue
        row = session.get(ToolCallRow, tool.tool_call_id)
        if row is None:
            row = ToolCallRow(
                tool_call_id=tool.tool_call_id,
                span_id=tool.span_id,
                run_id=tool.run_id,
                project_id=project.id,
                agent_name=tool.agent_name,
                tool_name=tool.tool_name,
            )
            session.add(row)
        row.latency_ms = tool.latency_ms
        row.success = tool.success
        row.args_hash = tool.args_hash
        if tool.timestamp:
            row.timestamp = tool.timestamp
        run_ids.add(tool.run_id)

    for handoff in batch.handoffs:
        if handoff.project_id != project.id:
            continue
        row = session.get(HandoffRow, handoff.handoff_id)
        if row is None:
            row = HandoffRow(
                handoff_id=handoff.handoff_id,
                run_id=handoff.run_id,
                project_id=project.id,
                from_span_id=handoff.from_span_id,
                to_span_id=handoff.to_span_id,
            )
            session.add(row)
        row.reason = handoff.reason
        if handoff.timestamp:
            row.timestamp = handoff.timestamp
        run_ids.add(handoff.run_id)

    session.flush()
    for run_id in run_ids:
        _recompute_run_aggregates(session, run_id)

    session.commit()
    return {
        "ok": True,
        "project_id": project.id,
        "runs": len(batch.runs),
        "spans": len(batch.spans),
        "llm_calls": len(batch.llm_calls),
        "tool_calls": len(batch.tool_calls),
        "handoffs": len(batch.handoffs),
    }


def _recompute_run_aggregates(session: Session, run_id: str) -> None:
    run = session.get(RunRow, run_id)
    if run is None:
        return
    spans = session.exec(select(SpanRow).where(SpanRow.run_id == run_id)).all()
    calls = session.exec(select(LLMCallRow).where(LLMCallRow.run_id == run_id)).all()
    run.span_count = len(spans)
    run.total_tokens = sum(c.total_tokens for c in calls)
    run.total_cost_usd = round(sum(c.cost_usd for c in calls), 8)
    run.duration_ms = _duration_ms(run.started_at, run.ended_at)
