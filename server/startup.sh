#!/usr/bin/env bash
# TelemetryBot collector / Azure App Service startup
#
# Same Oryx pitfalls as sales-ivr/startup.sh:
# 1) Oryx extracts the built app to /tmp/<id> and only puts antenv on PYTHONPATH.
# 2) /home/site/wwwroot can still contain an empty/broken app/ directory.
#    Never trust "-d app" under wwwroot.
# 3) Derive APP_ROOT from the live antenv path on sys.path (always correct).

set -uo pipefail

PORT="${PORT:-8000}"

APP_ROOT="$(
  python - <<'PY'
import sys
from pathlib import Path

for entry in sys.path:
    p = Path(entry)
    # .../antenv/lib/python3.x/site-packages
    if p.name == "site-packages" and "antenv" in p.parts:
        # site-packages -> python3.x -> lib -> antenv -> app root
        print(p.resolve().parents[3])
        break
else:
    print("")
PY
)"

if [ -z "${APP_ROOT}" ] || [ ! -d "${APP_ROOT}" ]; then
  APP_ROOT="${APP_PATH:-${PWD:-/home/site/wwwroot}}"
fi

cd "${APP_ROOT}" || exit 1
export PYTHONPATH="${APP_ROOT}:${PYTHONPATH:-}"

# Persist SQLite on the App Service fileshare (wwwroot /tmp extract is ephemeral).
if [ -z "${DATABASE_URL:-}" ] || [ "${DATABASE_URL}" = "sqlite:///./telemetrybot.db" ]; then
  mkdir -p /home/data
  export DATABASE_URL="sqlite:////home/data/telemetrybot.db"
fi

echo "TelemetryBot collector startup: APP_ROOT=${APP_ROOT}"
echo "TelemetryBot collector startup: DATABASE_URL=${DATABASE_URL}"
echo "TelemetryBot collector startup: listing APP_ROOT (first 40):"
ls -la "${APP_ROOT}" | head -n 40 || true

if [ ! -f "${APP_ROOT}/asgi.py" ]; then
  echo "TelemetryBot collector startup: FATAL — ${APP_ROOT}/asgi.py missing" >&2
  exit 1
fi

if ! python -c "from app.main import app" 2>/dev/null; then
  echo "TelemetryBot collector startup: FATAL — cannot import app.main from ${APP_ROOT}" >&2
  python -c "import sys; print('sys.path=', sys.path)" >&2 || true
  ls -la "${APP_ROOT}/app" 2>&1 | head -n 20 >&2 || true
  exit 1
fi

exec gunicorn \
  -w 2 \
  -k uvicorn.workers.UvicornWorker \
  --chdir "${APP_ROOT}" \
  --pythonpath "${APP_ROOT}" \
  asgi:app \
  --bind=0.0.0.0:"${PORT}"
