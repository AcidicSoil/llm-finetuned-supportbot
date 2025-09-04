#!/usr/bin/env bash
set -Eeuo pipefail

# Install project pre-commit hook into .git/hooks for this clone (Linux/macOS)

ROOT_DIR="$(git rev-parse --show-toplevel)"
cd "$ROOT_DIR"

SRC=".github/hooks/pre-commit"
DST=".git/hooks/pre-commit"

if [[ ! -f "$SRC" ]]; then
  echo "[install-hooks] Missing $SRC. Aborting." >&2
  exit 1
fi

install -m 0755 "$SRC" "$DST"
echo "[install-hooks] Installed $SRC -> $DST"

if command -v git >/dev/null 2>&1; then
  git update-index --chmod=+x "$SRC" 2>/dev/null || true
fi

echo "[install-hooks] Done. Pre-commit hook active for this repo."

