"""Optional demo seed and coverage helpers for ADO Pipeline tab."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def demo_seed() -> int:
    """Emit one synthetic span so the ADO tab can be demoed (--demo-seed)."""
    try:
        from agentelemetry import TelemetryClient
        from agentelemetry.schemas import Channel
    except ImportError:
        print("agentelemetry not installed", file=sys.stderr)
        return 1

    client = TelemetryClient.from_config(ROOT / "telemetry.yaml")
    with client.start_run(external_id="ado-demo-001", channel=Channel.DEMO) as run:
        with client.span("ADO.SyncAgent"):
            client.record_llm_call(
                agent_name="ADO.SyncAgent",
                model="gpt-4o-mini",
                prompt_tokens=50,
                completion_tokens=20,
                total_tokens=70,
                latency_ms=40,
                finish_reason="stop",
            )
        run.outcome = "demo_ok"
    print("Seeded synthetic ADO.SyncAgent run")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="ADO Pipeline telemetry helpers")
    parser.add_argument(
        "--demo-seed",
        action="store_true",
        help="Emit a synthetic demo span (not real agent traffic)",
    )
    args = parser.parse_args()
    if args.demo_seed:
        return demo_seed()
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
