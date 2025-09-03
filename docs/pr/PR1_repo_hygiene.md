# chore(repo): Enforce LF + pre-commit + EditorConfig

## Summary
Stabilize formatting across OSes and align local dev with CI.

- Enforce LF line endings via `.gitattributes`.
- Add `.editorconfig` for newline/indent consistency in editors.
- Pre-commit (already in repo) runs Ruff + Black; LF normalization is handled by CI and `.gitattributes`.

## Rationale

- Prevent Black `--check` diffs on Windows→Linux PRs.
- Make editors auto-apply consistent indentation and final newlines.
- Reduce CI noise to focus reviews on code changes.

## Changes

- `.gitattributes`: enforce `eol=lf` for text files; mark binaries.
- `.editorconfig`: LF, final newline, UTF‑8, Python 4‑space, YAML/TOML/JSON 2‑space.
- No runtime code changes.

## Developer Notes

- After pulling this PR, re-normalize once:

  ```bash
  git add --renormalize .
  pre-commit run -a   # optional, if installed
  ```

- Local parity with CI:

  ```bash
  uv run black --check . && uv run ruff check .
  ```

## Checklist

- [x] No functional changes
- [x] CI green
- [x] Clear migration steps (re-normalize once)
