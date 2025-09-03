## Title

feat(scope): one-line summary

## TL;DR

<!-- Briefly describe what changed and why. Call out reviewer focus. -->

## Motivation & Context

<!-- Why is this change needed? What problems does it solve? -->

## Changes

- <!-- Bullet notable changes (files/subsystems, flags, configs). -->

## Test Plan

```bash
# Offline unit tests
export HF_HUB_OFFLINE=1
uv run pytest -q

# Optional online smoke
export HF_HUB_OFFLINE=0
export TEST_TINY_MODEL_ID=sshleifer/tiny-gpt2
uv run pytest -q -m smoke tests/smoke
```

## Screenshots / Logs (optional)

<!-- Paste output, screenshots, or links to artifacts. -->

## Validation Checklist

- [ ] CI green (lint, format, tests)
- [ ] `pre-commit run -a` is clean
- [ ] Rebased on latest `main`
- [ ] Scope limited to title/description
- [ ] README/docs updated (if applicable)
- [ ] Tests added/updated; names are descriptive
- [ ] Backward-compat verified or migration noted

## Linked issues / bugs

<!-- Closes #123 / Fixes #456 / Resolves #789 -->
