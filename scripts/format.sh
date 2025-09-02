#!/usr/bin/env bash
set -euo pipefail

# Auto-fix lint and format
if command -v uv >/dev/null 2>&1; then
  uv run ruff check . --fix
  uv run black .
else
  ruff check . --fix
  black .
fi

echo "Applied Ruff fixes and Black formatting."

