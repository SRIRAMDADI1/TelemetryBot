from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from sqlmodel import Session, select

from app.db.session import LLMCallRow, RunRow, SpanRow, ToolCallRow


SUCCESS_OUTCOMES = {
    "quoted",
    "succeeded",
    "completed",
    "handoff",
    "demo_ok",
    "success",
}


def _percentile(sorted_values: list[int], pct: float) -> int:
    """Nearest-rank percentile on a pre-sorted ascending list."""
    if not sorted_values:
        return 0
    if len(sorted_values) == 1:
        return sorted_values[0]
    # rank index in [0, n-1]
    idx = int(round((pct / 100.0) * (len(sorted_values) - 1)))
    return sorted_values[max(0, min(idx, len(sorted_values) - 1))]


def _is_successful(run: RunRow) -> bool:
    """Prefer an explicit outcome when present so intermediate turns don't count."""
    outcome = (run.outcome or "").lower().strip()
    if outcome:
        return outcome in SUCCESS_OUTCOMES
    return run.status == "succeeded"


def agent_stats(session: Session, project_id: str, limit_runs: int = 100) -> list[dict]:
    runs = session.exec(
        select(RunRow)
        .where(RunRow.project_id == project_id)
        .order_by(RunRow.started_at.desc())
        .limit(limit_runs)
    ).all()
    run_ids = [r.run_id for r in runs]
    if not run_ids:
        return []

    calls = session.exec(
        select(LLMCallRow).where(
            LLMCallRow.project_id == project_id,
            LLMCallRow.run_id.in_(run_ids),
        )
    ).all()
    spans = session.exec(
        select(SpanRow).where(
            SpanRow.project_id == project_id,
            SpanRow.run_id.in_(run_ids),
        )
    ).all()
    tools = session.exec(
        select(ToolCallRow).where(
            ToolCallRow.project_id == project_id,
            ToolCallRow.run_id.in_(run_ids),
        )
    ).all()

    by_agent: dict[str, dict] = defaultdict(
        lambda: {
            "agent_name": "",
            "runs": set(),
            "spans": 0,
            "errors": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "cost_usd": 0.0,
            "latency_ms": 0,
            "llm_calls": 0,
            "tool_calls": 0,
            "tool_errors": 0,
        }
    )

    for span in spans:
        row = by_agent[span.agent_name]
        row["agent_name"] = span.agent_name
        row["spans"] += 1
        row["runs"].add(span.run_id)
        row["latency_ms"] += span.latency_ms
        if span.status == "error":
            row["errors"] += 1

    for call in calls:
        row = by_agent[call.agent_name]
        row["agent_name"] = call.agent_name
        row["runs"].add(call.run_id)
        row["prompt_tokens"] += call.prompt_tokens
        row["completion_tokens"] += call.completion_tokens
        row["total_tokens"] += call.total_tokens
        row["cost_usd"] += call.cost_usd
        row["latency_ms"] += call.latency_ms
        row["llm_calls"] += 1

    for tool in tools:
        row = by_agent[tool.agent_name]
        row["agent_name"] = tool.agent_name
        row["runs"].add(tool.run_id)
        row["tool_calls"] += 1
        if not tool.success:
            row["tool_errors"] += 1

    result = []
    for row in by_agent.values():
        run_count = len(row["runs"])
        tool_calls = row["tool_calls"]
        cost = row["cost_usd"]
        result.append(
            {
                "agent_name": row["agent_name"],
                "run_count": run_count,
                "span_count": row["spans"],
                "error_count": row["errors"],
                "prompt_tokens": row["prompt_tokens"],
                "completion_tokens": row["completion_tokens"],
                "total_tokens": row["total_tokens"],
                "cost_usd": round(cost, 8),
                "cost_per_run": round(cost / run_count, 8) if run_count else 0.0,
                "avg_latency_ms": int(row["latency_ms"] / max(row["llm_calls"] or row["spans"], 1)),
                "llm_calls": row["llm_calls"],
                "error_rate": round(row["errors"] / max(row["spans"], 1), 4),
                "tool_calls": tool_calls,
                "tool_errors": row["tool_errors"],
                "tool_error_rate": round(row["tool_errors"] / max(tool_calls, 1), 4),
            }
        )
    result.sort(key=lambda r: r["cost_usd"], reverse=True)
    return result


def efficiency_metrics(session: Session, project_id: str, limit_runs: int = 200) -> dict:
    empty = {
        "project_id": project_id,
        "run_count": 0,
        "successful_runs": 0,
        "success_rate": 0.0,
        "total_cost_usd": 0.0,
        "cost_per_outcome": 0.0,
        "waste_ratio": 0.0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "p50_latency_ms": 0,
        "p95_latency_ms": 0,
        "tool_call_count": 0,
        "tool_error_count": 0,
        "tool_error_rate": 0.0,
        "model_mix": [],
        "leaderboard": [],
        "today_run_count": 0,
        "today_cost_usd": 0.0,
        "avg_tokens_per_run": 0,
    }

    runs = session.exec(
        select(RunRow)
        .where(RunRow.project_id == project_id)
        .order_by(RunRow.started_at.desc())
        .limit(limit_runs)
    ).all()
    if not runs:
        return empty

    run_ids = [r.run_id for r in runs]
    calls = session.exec(
        select(LLMCallRow).where(
            LLMCallRow.project_id == project_id,
            LLMCallRow.run_id.in_(run_ids),
        )
    ).all()
    spans = session.exec(
        select(SpanRow).where(
            SpanRow.project_id == project_id,
            SpanRow.run_id.in_(run_ids),
        )
    ).all()
    tools = session.exec(
        select(ToolCallRow).where(
            ToolCallRow.project_id == project_id,
            ToolCallRow.run_id.in_(run_ids),
        )
    ).all()

    total_cost = sum(r.total_cost_usd for r in runs)
    successful = [r for r in runs if _is_successful(r)]
    success_count = len(successful)
    cost_per_outcome = (total_cost / success_count) if success_count else 0.0
    success_rate = success_count / len(runs)

    error_span_ids = {s.span_id for s in spans if s.status == "error"}
    waste_tokens = sum(c.total_tokens for c in calls if c.span_id in error_span_ids)
    total_tokens = sum(c.total_tokens for c in calls) or 1
    waste_ratio = waste_tokens / total_tokens

    prompt_tokens = sum(c.prompt_tokens for c in calls)
    completion_tokens = sum(c.completion_tokens for c in calls)

    durations = sorted(r.duration_ms for r in runs)
    p50_latency_ms = _percentile(durations, 50)
    p95_latency_ms = _percentile(durations, 95)

    tool_call_count = len(tools)
    tool_error_count = sum(1 for t in tools if not t.success)
    tool_error_rate = tool_error_count / max(tool_call_count, 1)

    model_totals: dict[str, dict] = defaultdict(lambda: {"model": "", "cost_usd": 0.0, "tokens": 0})
    for call in calls:
        row = model_totals[call.model]
        row["model"] = call.model
        row["cost_usd"] += call.cost_usd
        row["tokens"] += call.total_tokens
    model_mix = sorted(
        [
            {
                "model": v["model"],
                "cost_usd": round(v["cost_usd"], 8),
                "tokens": v["tokens"],
            }
            for v in model_totals.values()
        ],
        key=lambda x: x["cost_usd"],
        reverse=True,
    )

    # cost_per_run already set inside agent_stats; keep a legacy alias for old clients
    leaderboard = agent_stats(session, project_id, limit_runs)
    for item in leaderboard:
        item["efficiency"] = item["cost_per_run"]

    today = datetime.now(timezone.utc).date()
    today_runs = [
        r
        for r in runs
        if (r.started_at.date() if r.started_at.tzinfo else r.started_at.replace(tzinfo=timezone.utc).date())
        == today
    ]

    return {
        "project_id": project_id,
        "run_count": len(runs),
        "successful_runs": success_count,
        "success_rate": round(success_rate, 4),
        "total_cost_usd": round(total_cost, 8),
        "cost_per_outcome": round(cost_per_outcome, 8),
        "waste_ratio": round(waste_ratio, 4),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "p50_latency_ms": p50_latency_ms,
        "p95_latency_ms": p95_latency_ms,
        "tool_call_count": tool_call_count,
        "tool_error_count": tool_error_count,
        "tool_error_rate": round(tool_error_rate, 4),
        "model_mix": model_mix,
        "leaderboard": leaderboard,
        "today_run_count": len(today_runs),
        "today_cost_usd": round(sum(r.total_cost_usd for r in today_runs), 8),
        "avg_tokens_per_run": int(
            (sum(r.total_tokens for r in runs) / len(runs)) if runs else 0
        ),
    }


def compare_runs(session: Session, run_a: str, run_b: str) -> dict:
    a = session.get(RunRow, run_a)
    b = session.get(RunRow, run_b)
    if a is None or b is None:
        return {"error": "one or both runs not found"}
    return {
        "run_a": _run_summary(session, a),
        "run_b": _run_summary(session, b),
        "diff": {
            "cost_usd": round(b.total_cost_usd - a.total_cost_usd, 8),
            "tokens": b.total_tokens - a.total_tokens,
            "duration_ms": b.duration_ms - a.duration_ms,
            "span_count": b.span_count - a.span_count,
        },
    }


def _run_summary(session: Session, run: RunRow) -> dict:
    spans = session.exec(select(SpanRow).where(SpanRow.run_id == run.run_id)).all()
    return {
        "run_id": run.run_id,
        "external_id": run.external_id,
        "status": run.status,
        "outcome": run.outcome,
        "channel": run.channel,
        "experiment": run.experiment,
        "total_tokens": run.total_tokens,
        "total_cost_usd": run.total_cost_usd,
        "duration_ms": run.duration_ms,
        "span_count": run.span_count,
        "agents": sorted({s.agent_name for s in spans}),
    }
