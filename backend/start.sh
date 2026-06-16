#!/bin/bash
# Run database migrations (from repo root where alembic.ini lives)
cd "$(dirname "$0")/.."
alembic upgrade head 2>&1 || echo "Migration failed, continuing..."
cd "$(dirname "$0")"
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --workers 1 --timeout-keep-alive 30
