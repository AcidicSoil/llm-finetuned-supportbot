# Creates a GitHub PR from the current repo and optionally merges it.
# Usage examples (run from repo root):
#   pwsh -File scripts/open_pr.ps1
#   pwsh -File scripts/open_pr.ps1 -Merge
#   pwsh -File scripts/open_pr.ps1 -Merge -TagRelease -Tag v0.4.0

param(
  [string]$Base = "main",
  [string]$Head = "",
  [switch]$Merge,
  [switch]$TagRelease,
  [string]$Tag = "",
  [string]$Repo = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Require-Cmd {
  param([Parameter(Mandatory=$true)][string]$Name)
  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    throw "Command '$Name' not found. Install it and re-run."
  }
}

Require-Cmd git
Require-Cmd gh

# Ensure we are inside a git repo
& git rev-parse --is-inside-work-tree *> $null
if ($LASTEXITCODE -ne 0) { throw "Not inside a Git repository." }

# Ensure GitHub CLI is authenticated
& gh auth status *> $null
if ($LASTEXITCODE -ne 0) { throw "GitHub CLI not authenticated. Run 'gh auth login' and retry." }

# Resolve repo if not provided
if (-not $Repo) {
  $origin = git remote get-url origin 2>$null
  if (-not $origin) { throw "No 'origin' remote found; set -Repo owner/name or add a remote." }
  $Repo = $origin
}

# Resolve HEAD to current branch if not provided, then ensure we're on it
if (-not $Head) {
  $Head = git branch --show-current
}
$current = git branch --show-current
if ($current -ne $Head) {
  Write-Host "Switching to '$Head' (current: '$current')..."
  & git checkout $Head
}

# Ensure branch is pushed and has upstream
try {
  & git rev-parse --abbrev-ref --symbolic-full-name '@{u}' *> $null
  if ($LASTEXITCODE -ne 0) { throw "no-upstream" }
} catch {
  Write-Host "No upstream set for '$Head'. Pushing to origin..."
  & git push -u origin $Head
}

$title = 'Enforce preset<config<CLI precedence; doc "uv" flow; add PR scripts'

$body = @"
Summary
- Enforces explicit precedence: preset < config file < CLI
- Makes train_lora import path lightweight for arg-parse/unit tests
- Adds uv cheatsheet and aligns docs to uv-first workflow
- Adds PR automation scripts for Bash/PowerShell; fixes PowerShell '@{u}' quoting

Changes
- scripts/train_lora.py: lazy-import heavy deps; precedence handling
- instructions/uv-cheatsheet.md: new
- scripts/open_pr.ps1, scripts/open_pr.sh: new (+ quoting fix)

Testing
- Unit/arg-parse tests confirmed passing on 2025-09-03

Notes
- Follow-up: open PR for 'feature/taskmaster' (currently +45 ahead of 'main')
- Labels: feature, docs, tooling
"@

Write-Host "Creating PR: $Head -> $Base ..."
& gh pr create -R $Repo -B $Base -H $Head -t $title -b $body --label feature --label docs --label tooling

# Fetch PR info
$prJson = & gh pr view --head $Head --json number,url -q "{number: .number, url: .url}"
if (-not $prJson) { throw "Unable to retrieve PR details for head '$Head'." }
$pr = $prJson | ConvertFrom-Json
Write-Host ("PR #{0}: {1}" -f $pr.number, $pr.url)

if ($Merge) {
  Write-Host "Merging PR #$($pr.number) with --squash and deleting branch..."
  & gh pr merge $pr.number --squash --delete-branch
}

if ($TagRelease) {
  if (-not $Tag) {
    $Tag = Read-Host "Enter release tag (e.g., v0.4.0)"
  }
  if (-not $Tag) { throw "Tag name is required for release creation." }
  Write-Host "Creating release '$Tag' with generated notes..."
  & gh release create $Tag --generate-notes -t $Tag
}

Write-Host "Done."
