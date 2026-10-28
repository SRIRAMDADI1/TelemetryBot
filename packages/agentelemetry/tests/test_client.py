from agentelemetry.client import TelemetryClient
from agentelemetry.config import TelemetryConfig
from agentelemetry.decorators import trace_agent
from agentelemetry.llm import record_llm_usage
from agentelemetry.schemas import IngestBatch


class CaptureTransport:
    def __init__(self) -> None:
        self.batches: list[IngestBatch] = []

    def send_batch(self, batch: IngestBatch) -> dict:
        self.batches.append(batch)
        return {"ok": True}


def test_start_run_span_llm_flush():
    transport = CaptureTransport()
    client = TelemetryClient(
        TelemetryConfig(collector_url="http://test", project_id="sales-ivr", api_key="k"),
        transport=transport,  # type: ignore[arg-type]
    )

    with client.start_run(external_id="t1", channel="cli") as run:

        @trace_agent("QuoteGenerationAgent")
        def quote() -> str:
            record_llm_usage(
                agent_name="QuoteGenerationAgent",
                model="gpt-4o-mini",
                prompt_tokens=10,
                completion_tokens=5,
                total_tokens=15,
                latency_ms=12,
            )
            return "done"

        assert quote() == "done"
        run.outcome = "quoted"

    assert len(transport.batches) == 1
    batch = transport.batches[0]
    assert len(batch.runs) >= 1
    assert len(batch.spans) == 1
    assert batch.spans[0].agent_name == "QuoteGenerationAgent"
    assert len(batch.llm_calls) == 1
    assert batch.llm_calls[0].cost_usd > 0
