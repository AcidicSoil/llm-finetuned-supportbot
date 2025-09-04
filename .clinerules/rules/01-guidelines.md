# Cline Rules — Guidelines

## Coding & Style

- Python: PEP8, 4 spaces; type hints where practical.
- Keep functions small; prefer pure functions for data transforms.
- Avoid one-letter names; no inline copyright headers.

## Testing & Verification

- Prefer fast, local checks first: `uv run pytest -q` if tests exist.
- For script changes, add a smoke run target (dry run or small batch).
- Do not fix unrelated failing tests; call them out in notes.

## Documentation

- Update `README.md` when UX or commands change.
- Record decisions/tradeoffs in `memory-bank/systemPatterns.md`.
- Update `memory-bank/progress.md` after milestones.

## Changes

- Keep diffs minimal and focused; match existing code style.
- Avoid renames/refactors unless required by the task.
