#!/bin/sh
set -eu

if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
  alembic upgrade head
fi
exec uvicorn backend.main:app --host 0.0.0.0 --port 8000
