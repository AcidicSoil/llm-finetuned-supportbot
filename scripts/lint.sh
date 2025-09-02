#!/usr/bin/env bash
set -euo pipefail

# Lint (CI parity)
if command -v uv >/dev/null 2>&1; then
  uv run ruff check .
  uv run black --check .
else
  ruff check .
  black --check .
fi

echo "Lint checks passed."
