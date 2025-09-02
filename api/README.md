# Inference API (FastAPI)

Minimal service exposing:

- `GET /healthz` → `{ "status": "ok" }`
- `POST /generate` → `{ "generated_text": str | list[str] }`

Auth stub: send header `X-API-Key` matching the `API_KEY` env var (defaults to `devkey`).

## Install & Run

This project uses `uv`.

1) Add deps (already in `pyproject.toml`): `fastapi[standard]`, `uvicorn`
2) Sync env: `uv sync --dev`
3) Run server:

```bash
uv run uvicorn api.main:app --host 0.0.0.0 --port 8000
```

Or use the helper script:

```bash
./run.sh
```

## Examples

Health check:

```bash
curl -s http://localhost:8000/healthz
```

Single prompt:

```bash
curl -s \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: devkey' \
  -d '{"prompt":"hello"}' \
  http://localhost:8000/generate | jq
```

Batch prompts:

```bash
curl -s \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: devkey' \
  -d '{"prompt":["hello","world"]}' \
  http://localhost:8000/generate | jq
```
