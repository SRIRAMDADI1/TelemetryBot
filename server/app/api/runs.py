from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.api.deps import require_user
from app.db.session import HandoffRow, LLMCallRow, Project, RunRow, SpanRow, ToolCallRow, User, get_session
from app.services.seed import user_can_access_project

router = APIRouter()


def _require_project(session: Session, user: User, project_id: str) -> Project:
    project = session.get(Project, project_id)
    if project is None:
        project = session.exec(select(Project).where(Project.slug == project_id)).first()
    if project is None or not user_can_access_project(user, project):
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("/runs")
def list_runs(
    project_id: str = Query(...),
    limit: int = Query(50, ge=1, le=500),
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
) -> list[dict]:
    _require_project(session, user, project_id)
    rows = session.exec(
        select(RunRow)
        .where(RunRow.project_id == project_id)
        .order_by(RunRow.started_at.desc())
        .limit(limit)
    ).all()
    return [
        {
            "run_id": r.run_id,
            "project_id": r.project_id,
            "external_id": r.external_id,
            "status": r.status,
            "channel": r.channel,
            "outcome": r.outcome,
            "experiment": r.experiment,
            "started_at": r.started_at,
            "ended_at": r.ended_at,
            "total_tokens": r.total_tokens,
            "total_cost_usd": r.total_cost_usd,
            "span_count": r.span_count,
            "duration_ms": r.duration_ms,
        }
        for r in rows
    ]


@router.get("/runs/{run_id}")
def get_run(
    run_id: str,
    session: Session = Depends(get_session),
    user: User = Depends(require_user),
) -> dict:
    run = session.get(RunRow, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    _require_project(session, user, run.project_id)
    spans = session.exec(
        select(SpanRow).where(SpanRow.run_id == run_id).order_by(SpanRow.started_at)
    ).all()
    calls = session.exec(
        select(LLMCallRow).where(LLMCallRow.run_id == run_id).order_by(LLMCallRow.timestamp)
    ).all()
    tools = session.exec(
        select(ToolCallRow).where(ToolCallRow.run_id == run_id).order_by(ToolCallRow.timestamp)
    ).all()
    handoffs = session.exec(select(HandoffRow).where(HandoffRow.run_id == run_id)).all()

    return {
        "run": {
            "run_id": run.run_id,
            "project_id": run.project_id,
            "external_id": run.external_id,
            "status": run.status,
            "channel": run.channel,
            "outcome": run.outcome,
            "experiment": run.experiment,
            "started_at": run.started_at,
            "ended_at": run.ended_at,
            "total_tokens": run.total_tokens,
            "total_cost_usd": run.total_cost_usd,
            "span_count": run.span_count,
            "duration_ms": run.duration_ms,
            "metadata": run.metadata_json,
        },
        "spans": [
            {
                "span_id": s.span_id,
                "parent_span_id": s.parent_span_id,
                "agent_name": s.agent_name,
                "status": s.status,
                "started_at": s.started_at,
                "ended_at": s.ended_at,
                "latency_ms": s.latency_ms,
                "error": s.error,
            }
            for s in spans
        ],
        "llm_calls": [
            {
                "call_id": c.call_id,
                "span_id": c.span_id,
                "agent_name": c.agent_name,
                "model": c.model,
                "prompt_tokens": c.prompt_tokens,
                "completion_tokens": c.completion_tokens,
                "total_tokens": c.total_tokens,
                "latency_ms": c.latency_ms,
                "cost_usd": c.cost_usd,
                "finish_reason": c.finish_reason,
                "timestamp": c.timestamp,
            }
            for c in calls
        ],
        "tool_calls": [
            {
                "tool_call_id": t.tool_call_id,
                "span_id": t.span_id,
                "agent_name": t.agent_name,
                "tool_name": t.tool_name,
                "latency_ms": t.latency_ms,
                "success": t.success,
            }
            for t in tools
        ],
        "handoffs": [
            {
                "handoff_id": h.handoff_id,
                "from_span_id": h.from_span_id,
                "to_span_id": h.to_span_id,
                "reason": h.reason,
            }
            for h in handoffs
        ],
    }
