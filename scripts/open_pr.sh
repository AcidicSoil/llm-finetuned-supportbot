#!/usr/bin/env bash
set -euo pipefail

# Create a GitHub PR from current repo, optionally squash-merge and tag a release.
# Usage:
#   bash scripts/open_pr.sh [-B base] [-H head] [-R owner/repo] [-m] [--tag TAG]
# Examples:
#   bash scripts/open_pr.sh
#   bash scripts/open_pr.sh -m
#   bash scripts/open_pr.sh -m --tag v0.4.0

BASE="main"
HEAD="feat/presets-cli-precedence"
REPO=""
DO_MERGE=false
TAG_RELEASE=""

print_usage() {
  echo "Usage: $0 [-B base] [-H head] [-R owner/repo] [-m] [--tag TAG]" >&2
}

# Parse short/long flags
while (( $# )); do
  case "$1" in
    -B) BASE=${2:-}; shift 2 ;;
    -H) HEAD=${2:-}; shift 2 ;;
    -R) REPO=${2:-}; shift 2 ;;
    -m|--merge) DO_MERGE=true; shift ;;
    --tag) TAG_RELEASE=${2:-}; shift 2 ;;
    -h|--help) print_usage; exit 0 ;;
    --) shift; break ;;
    -*) echo "Unknown option: $1" >&2; print_usage; exit 2 ;;
    *) break ;;
  esac
done

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || { echo "Missing required command: $1" >&2; exit 127; }
}

require_cmd git
require_cmd gh

# Ensure we are in a git repo
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Not inside a Git repository." >&2
  exit 1
fi

# Ensure gh is authenticated (non-interactive check)
if ! gh auth status >/dev/null 2>&1; then
  echo "GitHub CLI not authenticated. Run: gh auth login" >&2
  exit 1
fi

# Resolve repo from origin if not provided
if [[ -z "$REPO" ]]; then
  if ! origin_url=$(git remote get-url origin 2>/dev/null); then
    echo "No 'origin' remote found; supply -R OWNER/REPO." >&2
    exit 1
  fi
  REPO="$origin_url"
fi

current_branch=$(git branch --show-current)
if [[ "$current_branch" != "$HEAD" ]]; then
  echo "Switching to '$HEAD' (current: '$current_branch')..."
  git checkout "$HEAD"
fi

# Ensure upstream exists; push if needed
if ! git rev-parse --abbrev-ref --symbolic-full-name @{u} >/dev/null 2>&1; then
  echo "Setting upstream and pushing '$HEAD' to origin..."
  git push -u origin "$HEAD"
fi

TITLE='feat(train,presets): enforce preset<config<CLI precedence + uv docs'
read -r -d '' BODY <<'EOF'
Summary
- Enforce precedence: preset < config < CLI
- Add --auto-precision (use bf16 when supported)
- Enforce mutual exclusivity: --bf16 / --fp16 at parse time
- Add unit tests + docstrings for presets precedence
- Update docs: how to run preset tests with uv

Details
This PR formalizes the CLI/config/preset precedence rules to prevent unexpected overrides when combining YAML presets, explicit config files, and command-line flags. It also adds an --auto-precision convenience flag and guards against invalid precision flag combinations. Docs updated to prefer uv for environment and test runs.

Notes
- Ensure branch is pushed: git push -u origin HEAD
EOF

echo "Creating PR: $HEAD -> $BASE ..."
if ! gh pr create -R "$REPO" -B "$BASE" -H "$HEAD" -t "$TITLE" -b "$BODY" >/dev/null; then
  echo "PR create failed (it may already exist). Continuing to fetch details..." >&2
fi

# Retrieve PR number + URL for the head branch
PR_JSON=$(gh pr view -R "$REPO" --head "$HEAD" --json number,url 2>/dev/null || true)
if [[ -z "$PR_JSON" ]]; then
  echo "Unable to retrieve PR details for head '$HEAD'." >&2
  exit 1
fi

PR_NUMBER=$(printf '%s' "$PR_JSON" | grep -o '"number"[^0-9]*[0-9]\+' | grep -o '[0-9]\+$' || true)
PR_URL=$(printf '%s' "$PR_JSON" | sed -n 's/.*"url"[[:space:]]*:[[:space:]]*"\([^"]\+\)".*/\1/p')

echo "PR #$PR_NUMBER: $PR_URL"

if $DO_MERGE; then
  echo "Squash-merging PR #$PR_NUMBER and deleting branch..."
  gh pr merge -R "$REPO" "$PR_NUMBER" --squash --delete-branch
fi

if [[ -n "$TAG_RELEASE" ]]; then
  echo "Creating release '$TAG_RELEASE' with generated notes..."
  gh release create -R "$REPO" "$TAG_RELEASE" --generate-notes -t "$TAG_RELEASE"
fi

echo "Done."

