#!/bin/bash
cd "$(dirname "$0")"
python run_migration.py
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --workers 1 --timeout-keep-alive 30
