# Data Schema

This project uses Pydantic v2 models to validate records used for fine-tuning and evaluation.

- Root model: `DataRecord`
- Fields:
  - `id: str` — non-empty identifier (trimmed)
  - `schema_version: str` — default `"1.0"`
  - `inputs: Inputs`
    - `question: str` — non-empty (trimmed)
    - `context: Optional[str]` — optional
  - `outputs: Outputs`
    - `answer: str` — non-empty (trimmed)
  - `meta: Meta`
    - `source: str` — non-empty (trimmed)
    - `timestamp: datetime` — ISO8601 date-time
    - `tags: List[str]` — non-empty strings; trimmed

Validation notes:

- Empty/whitespace-only strings are rejected for `id`, `question`, `answer`, and `source`.
- `tags` must not contain empty strings or nulls; values are trimmed.
- Dataset-level utility `validate_dataset(records, allowed_tags=None)` checks:
  - Duplicate `id`s
  - Basic PII heuristic (email/phone-like patterns) in `question`, `context`, or `answer`
  - Disallowed tags if a vocabulary is provided

## JSON Schema

A machine-readable JSON Schema is generated from the Pydantic model.

- Path: `schema/data_schema.json`
- Regenerate via: `uv run python scripts/generate_schema.py`

## Examples

Valid record:

```json
{
  "id": "ex-001",
  "schema_version": "1.0",
  "inputs": { "question": "How do I reset my password?" },
  "outputs": { "answer": "Click 'Forgot password' and follow the email link." },
  "meta": {
    "source": "support_portal",
    "timestamp": "2024-07-01T12:00:00Z",
    "tags": ["auth", "account"]
  }
}
```

Invalid record (empty strings + bad tag):

```json
{
  "id": " ",
  "inputs": { "question": "" },
  "outputs": { "answer": "   " },
  "meta": {
    "source": "",
    "timestamp": "2024-07-01T12:00:00Z",
    "tags": ["ok", " "]
  }
}
```

## Regeneration

- Ensure deps are installed: `uv sync --dev`
- Generate schema: `uv run python scripts/generate_schema.py`
- Run tests: `uv run pytest -q`

