# Workflow: PR Review

Ask AI: Review a pull request for correctness, style, and tests. Summarize high-impact feedback first.

```bash
# Install dependencies (Python)
pip install -r requirements.txt || true

# Run tests if present
pytest -q || true

# Lint (optional; skip if not configured)
pylint $(git ls-files '*.py') || true
```

<ask_followup_question>
If tests or lint fail, should I block the PR or proceed with a review focusing on code quality and potential risks?
</ask_followup_question>
