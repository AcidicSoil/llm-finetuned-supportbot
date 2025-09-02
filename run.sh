#!/usr/bin/env bash
set -euo pipefail

export API_KEY="${API_KEY:-devkey}"

exec uv run uvicorn api.main:app --host 0.0.0.0 --port 8000
