"""Emit a demo run to a local collector (or print the batch if unreachable)."""

from __future__ import annotations

import json
import os
import sys

from agentelemetry.client import TelemetryClient
from agentelemetry.config import TelemetryConfig
from agentelemetry.decorators import trace_agent
from agentelemetry.llm import record_llm_usage
from agentelemetry.schemas import Channel


def main() -> int:
    collector = os.environ.get("TELEMETRY_COLLECTOR_URL", "http://localhost:8100")
    api_key = os.environ.get("TELEMETRY_API_KEY", "dev-sales-ivr-key")
    project_id = os.environ.get("TELEMETRY_PROJECT_ID", "sales-ivr")

    config = TelemetryConfig(
        collector_url=collector,
        project_id=project_id,
        project_slug=project_id,
        api_key=api_key,
    )
    client = TelemetryClient(config)

    with client.start_run(external_id="demo-001", channel=Channel.DEMO) as run:

        @trace_agent("DemoAgent")
        def work() -> str:
            record_llm_usage(
                agent_name="DemoAgent",
                model="gpt-4o-mini",
                prompt_tokens=120,
                completion_tokens=40,
                total_tokens=160,
                latency_ms=85,
                finish_reason="stop",
            )
            return "ok"

        work()
        run.outcome = "demo_ok"

    print(
        json.dumps(
            {
                "run_id": run.run_id,
                "project_id": project_id,
                "collector": collector,
                "message": "Demo run flushed (check collector / dashboard)",
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
