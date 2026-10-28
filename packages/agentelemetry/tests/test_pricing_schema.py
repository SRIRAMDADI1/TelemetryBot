from agentelemetry.pricing import estimate_cost_usd, normalize_model
from agentelemetry.schemas import Channel, IngestBatch, RunEvent


def test_normalize_model_alias():
    assert normalize_model("gpt-4o-mini") == "gpt-4o-mini"
    assert normalize_model("my-gpt-4o-mini-deployment") == "gpt-4o-mini"


def test_estimate_cost():
    cost = estimate_cost_usd("gpt-4o-mini", prompt_tokens=1_000_000, completion_tokens=0)
    assert cost == 0.15


def test_ingest_batch_roundtrip():
    batch = IngestBatch(
        runs=[RunEvent(project_id="sales-ivr", channel=Channel.DEMO, external_id="x")]
    )
    data = batch.model_dump(mode="json")
    restored = IngestBatch.model_validate(data)
    assert restored.runs[0].project_id == "sales-ivr"
