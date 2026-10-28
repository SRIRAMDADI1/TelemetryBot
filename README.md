# TelemetryBot

Agent observability platform — track **token usage, cost, latency, and efficiency** across multi-agent workloads, with one **monitoring tab per repo/project**.

## Layout

| Path | Role |
|------|------|
| `packages/agentelemetry/` | Python SDK (`TelemetryClient`, `@trace_agent`, pricing) |
| `server/` | FastAPI collector + auth + query API (SQLite locally, Postgres in Compose) |
| `dashboard/` | Next.js UI (login-gated) with project tabs |
| `cli/` | `telemetry` CLI — login / connect / scan / projects |
| `sales-ivr/` | First-party instrumented workload (live traces) |
| `ado-pipeline/` | Second tab (registered; meta-agents not built yet) |
| `infra/` | Azure Bicep stub for later hosting |

## Auth (Subphase F2)

The dashboard opens on a **login screen**. Supported sign-in methods:

| Method | Notes |
|--------|--------|
| **Email + password** | Register or sign in |
| **Magic link** | Email-only; in `AUTH_DEV_MODE` the link is returned in the API response |
| **GitHub** | Sign in, or connect later from the user menu / Connect page |

### Demo account (seeded)

| | |
|--|--|
| Email | `demo@telemetrybot.dev` |
| Password | `demo` |

This account owns the seeded **Sales IVR** and **ADO Pipeline** tabs.

After sign-in, **Connect GitHub** and import a repo as a new tab via **+ Connect**. That only opens a destination. The repo still needs the **Pulse SDK** (`agentelemetry`) to send traces — see **Send traces from the repo** on an empty Overview.

Ingest remains API-key based (`X-API-Key`); query APIs require a session.

## Send traces from a connected repo

After the repo is already a Pulse tab, do this **in that repository** (not in the dashboard):

1. Install the SDK into that repo’s environment:

```powershell
pip install -e /path/to/Pulse/packages/agentelemetry
```

2. Add `telemetry.yaml` at that repo’s root. `api_key` is the project ingest key (it authenticates ingest; it is not a separate dashboard step):

```yaml
collector_url: http://localhost:8100
project_id: your-repo-slug
project_slug: your-repo-slug
api_key: ${TELEMETRY_API_KEY}
enabled: true
```

3. Instrument agent runs in that repo’s code:

```python
from agentelemetry import TelemetryClient, trace_agent, record_llm_usage

client = TelemetryClient.from_config("telemetry.yaml")

with client.start_run(external_id="run-1", channel="cli") as run:

    @trace_agent("MyAgent")
    def work():
        record_llm_usage(
            agent_name="MyAgent",
            model="gpt-4o-mini",
            prompt_tokens=120,
            completion_tokens=40,
        )
        return "ok"

    work()
    run.outcome = "succeeded"
```

4. Run that repo as usual, then refresh Pulse.

Local folders can skip GitHub: `telemetry login` then `telemetry connect ./your-repo` (still requires the SDK in that repo). Optional coverage: `telemetry scan ./your-repo --project your-repo-slug`.

## Quick start (local)

### 1. Install Python packages

```powershell
cd packages/agentelemetry; pip install -e ".[dev]"
cd ../../server; pip install -e ".[dev]"
cd ../cli; pip install -e .
cd ../sales-ivr; pip install -e ".[dev]"
```

### 2. Start the collector

```powershell
cd server
uvicorn app.main:app --reload --port 8100
```

Collector listens on **8100**. Seeds demo user + two projects: **Sales IVR** (`dev-sales-ivr-key`) and **ADO Pipeline** (`dev-ado-pipeline-key`).

### 3. Start the dashboard

```powershell
cd dashboard
npm install
npm run dev
```

Open http://localhost:3000 → **login** → use the demo credentials (or GitHub / magic link).

### Run Sales IVR + TelemetryBot together

| Service | Port | Command |
|---------|------|---------|
| Collector | 8100 | `cd server; uvicorn app.main:app --reload --port 8100` |
| Dashboard | 3000 | `cd dashboard; npm run dev` |
| Sales IVR web | 8000 | `cd sales-ivr; python -m sales_ivr.web.app` |

Chat at http://127.0.0.1:8000 — traces appear on the Sales IVR tab after you sign in at http://localhost:3000.

### 4. Generate traces

```powershell
# Demo SDK → collector
$env:TELEMETRY_API_KEY="dev-sales-ivr-key"
python -m agentelemetry.demo

# Sales IVR fixture (needs Azure OpenAI for real tokens; still emits spans when usage exists)
cd sales-ivr
python -m sales_ivr.cli auto_quote_ca.json

# Optional ADO synthetic demo span
cd ../ado-pipeline
python telemetry_smoke.py --demo-seed
```

### 5. CLI login / connect / scan

```powershell
telemetry login   # demo@telemetrybot.dev / demo
telemetry whoami
telemetry projects
telemetry connect ./sales-ivr
telemetry scan ./sales-ivr
telemetry scan ./ado-pipeline --project ado-pipeline
```

## OAuth (optional production)

Set these on the collector (leave `AUTH_DEV_MODE=true` for local mock GitHub):

```text
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
COLLECTOR_PUBLIC_URL=http://localhost:8100
DASHBOARD_URL=http://localhost:3000
AUTH_DEV_MODE=false   # require a real GitHub OAuth app
```

Callback URL to register with GitHub:

- `{COLLECTOR_PUBLIC_URL}/v1/auth/github/callback`

## Docker Compose

```powershell
docker compose up --build
```

- Collector: http://localhost:8100/health  
- Dashboard: http://localhost:3000 (login first)  
- Postgres: localhost:5432 (`telemetry` / `telemetry` / `telemetrybot`)

Public Azure deploy (**no Docker**) and Google Search Console: [WEB.md](WEB.md)

## API sketch

| Method | Path | Notes |
|--------|------|-------|
| `POST` | `/v1/auth/email/login` | Email + password → session |
| `POST` | `/v1/auth/email/magic` | Request magic link |
| `GET` | `/v1/auth/github/start` | GitHub OAuth (`intent=login\|connect`) |
| `GET` | `/v1/auth/me` | Current user |
| `GET` | `/v1/github/repos` | List repos (connected GitHub) |
| `POST` | `/v1/projects/from-github` | Import repo as tab |
| `POST` | `/v1/ingest` | `X-API-Key` project ingest key |
| `GET` | `/v1/projects` | Tabs for signed-in user |
| `GET` | `/v1/runs?project_id=` | Scoped runs |
| `GET` | `/v1/runs/{id}` | Waterfall payload |
| `GET` | `/v1/agents/stats?project_id=` | Per-agent aggregates |
| `GET` | `/v1/metrics/efficiency?project_id=` | Cost/outcome, waste, model mix |

## Workloads

- **Sales IVR** — see [sales-ivr/README.md](sales-ivr/README.md) for Azure OpenAI setup. Telemetry is soft-fail: missing collector does not break quoting.
- **ADO Pipeline** — backlog tools today; empty coverage until meta-agents exist. Optional `--demo-seed` only.
