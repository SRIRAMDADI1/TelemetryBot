# agentelemetry

Python SDK for Pulse (TelemetryBot) agent observability. A GitHub repo that is already a Pulse tab still needs this package running **in that repo** so traces reach the collector.

## Install

```powershell
pip install -e .\packages\agentelemetry
```

## In the connected repo

1. Put `telemetry.yaml` at the repo root (`api_key` is that tab’s ingest key):

```yaml
collector_url: http://localhost:8100
project_id: your-repo-slug
project_slug: your-repo-slug
api_key: ${TELEMETRY_API_KEY}
enabled: true
```

2. Instrument a run:

```python
from agentelemetry import TelemetryClient, trace_agent, record_llm_usage

client = TelemetryClient.from_config("telemetry.yaml")

with client.start_run(external_id="session-1", channel="cli") as run:

    @trace_agent("MyAgent")
    def run_agent():
        record_llm_usage(
            agent_name="MyAgent",
            model="gpt-4o-mini",
            prompt_tokens=120,
            completion_tokens=40,
        )

    run_agent()
    run.outcome = "succeeded"
```

3. Run this repo. Traces appear on that Pulse tab within a few seconds.

See the monorepo root README for collector setup.
