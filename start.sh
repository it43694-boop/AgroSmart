#!/bin/sh
set -e

echo "Starting AgroSmart: PORT=${PORT:-8000}"

# Ensure uvicorn is available and print path for debugging
which uvicorn || echo "uvicorn not found in PATH: $PATH"

exec uvicorn main:app \
  --host 0.0.0.0 \
  --port ${PORT:-8000} \
  --workers 1 \
  --loop uvloop \
  --http httptools \
  --access-log \
  --log-level info
