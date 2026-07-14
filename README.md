# TelemetryBot

Monorepo for agent observability demos. Current workload: **Sales IVR** —
multi-agent insurance sales flow powered by Azure OpenAI (or offline mock LLM).

## Quick start

```bash
cd sales-ivr
pip install -e ".[dev]"
python -m pytest
python -m sales_ivr.cli auto_quote_ca.json
```

See [sales-ivr/README.md](sales-ivr/README.md) for **Azure OpenAI setup**
(resource create → model deploy → API key → env vars).

## Layout

- `sales-ivr/` — LLM agent Sales IVR (this is the observable workload)
- `ado-pipeline/` — Azure DevOps backlog tools (future ADO meta-agents)
