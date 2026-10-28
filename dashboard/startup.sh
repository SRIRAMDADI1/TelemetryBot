#!/usr/bin/env bash
# TelemetryBot dashboard / Azure App Service (Node) startup

set -uo pipefail

PORT="${PORT:-3000}"
APP_ROOT="${APP_PATH:-${PWD:-/home/site/wwwroot}}"

cd "${APP_ROOT}" || exit 1

echo "TelemetryBot dashboard startup: APP_ROOT=${APP_ROOT} PORT=${PORT}"
echo "TelemetryBot dashboard startup: listing APP_ROOT (first 40):"
ls -la "${APP_ROOT}" | head -n 40 || true

if [ ! -d "${APP_ROOT}/node_modules/next" ]; then
  echo "TelemetryBot dashboard startup: FATAL — next is not installed in node_modules" >&2
  exit 1
fi

if [ ! -d "${APP_ROOT}/.next" ]; then
  echo "TelemetryBot dashboard startup: FATAL — .next missing (Oryx did not run npm run build)" >&2
  exit 1
fi

exec "${APP_ROOT}/node_modules/.bin/next" start -p "${PORT}"
