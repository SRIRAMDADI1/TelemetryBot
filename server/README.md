# TelemetryBot collector server

FastAPI collector: ingest, auth, project tabs, metrics.

## Run

```powershell
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8100
```

## Auth

- Demo user (seeded): `demo@telemetrybot.dev` / `demo`
- `AUTH_DEV_MODE=true` (default) enables mock GitHub sign-in without an OAuth app
- Query APIs require `Authorization: Bearer <session>` or `tb_session` cookie
- Ingest still uses `X-API-Key`

See root README for OAuth env vars.
