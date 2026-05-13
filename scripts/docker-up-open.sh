#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_URL="${CAREERAGENT_APP_URL:-http://localhost:3000/apply}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
VENV_PYTHON="$ROOT_DIR/backend/.venv/bin/python"

cd "$ROOT_DIR"

printf 'Starting CareerAgent database and frontend in Docker...\n'
docker compose stop backend >/dev/null 2>&1 || true
docker compose up --build -d db frontend

if [ ! -x "$VENV_PYTHON" ]; then
  printf 'Creating backend virtualenv...\n'
  "$PYTHON_BIN" -m venv "$ROOT_DIR/backend/.venv"
fi

printf 'Ensuring backend Python dependencies are installed...\n'
"$VENV_PYTHON" -m pip install -r "$ROOT_DIR/backend/requirements.txt"
"$VENV_PYTHON" -m playwright install chromium

open_app_when_ready() {
  for _ in $(seq 1 90); do
    if curl -fsS "http://localhost:${FRONTEND_PORT}" >/dev/null 2>&1 \
      && curl -fsS "http://localhost:${BACKEND_PORT}/health" >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done

  if command -v open >/dev/null 2>&1; then
    if open -na "Chromium" --args "$APP_URL" >/dev/null 2>&1; then
      return
    fi
    if open -na "Google Chrome" --args "$APP_URL" >/dev/null 2>&1; then
      return
    fi
    open "$APP_URL" >/dev/null 2>&1 || true
  fi

  printf 'CareerAgent is running at %s\n' "$APP_URL"
}

open_app_when_ready &

cd "$ROOT_DIR/backend"
printf 'Starting local backend on http://localhost:%s for native Chromium autofill...\n' "$BACKEND_PORT"
exec env \
  DATABASE_URL="${DATABASE_URL:-postgresql+psycopg2://careeragent:careeragent@localhost:${POSTGRES_PORT}/careeragent}" \
  POSTGRES_HOST="${POSTGRES_HOST:-localhost}" \
  POSTGRES_PORT="$POSTGRES_PORT" \
  BACKEND_PORT="$BACKEND_PORT" \
  FRONTEND_PORT="$FRONTEND_PORT" \
  PLAYWRIGHT_HEADLESS=false \
  PLAYWRIGHT_USE_XVFB=false \
  "$VENV_PYTHON" -m uvicorn main:app --reload --host 0.0.0.0 --port "$BACKEND_PORT"
