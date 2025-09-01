[![llm-finetune-supportbot](https://github.com/AcidicSoil/llm-finetuned-supportbot/actions/workflows/ci.yml/badge.svg)](https://github.com/AcidicSoil/llm-finetuned-supportbot/actions/workflows/ci.yml)
[![GitMCP](https://img.shields.io/endpoint?url=https://gitmcp.io/badge/acidicsoil/llm-finetune-supportbot)](https://gitmcp.io/acidicsoil/llm-finetune-supportbot)
**Repo:** `llm-finetune-supportbot` • **Last Updated:** 2025-08-19


# llm-finetune-supportbot

## Fine-tune a Small LLM on Support Data

## 🎯 Goal

Train a small open LLM on tech-support style conversations and evaluate improvements in helpfulness and accuracy.

## 🧱 Tech Stack

Python, PyTorch, Hugging Face Transformers, PEFT/LoRA, BitsAndBytes

## 🔗 Upstream / Tools Used

transformers, datasets, peft, trl

## ✅ Success Metrics

- Answer quality (win rate vs. base model on 100 eval questions)
- Hallucination rate (manual rubric)
- Training cost & time

## 🚀 Quickstart

```bash
# 1) Install project deps (incl. dev)
uv sync --dev

# 2) Run demo in the project env
uv run demo.py
```

### Inference API (FastAPI)

Run a minimal web service that exposes `/healthz` and `/generate`.

```bash
# Start the API (defaults API_KEY=devkey)
./run.sh

# Or explicitly:
uv run uvicorn api.main:app --host 0.0.0.0 --port 8000
```

Example requests:

```bash
# Health
curl -s http://localhost:8000/healthz

# Single prompt
curl -s \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: devkey' \
  -d '{"prompt":"hello"}' \
  http://localhost:8000/generate | jq

# Batch prompts
curl -s \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: devkey' \
  -d '{"prompt":["hello","world"]}' \
  http://localhost:8000/generate | jq
```

See `api/README.md` for details.

## 🛠️ Training (Config Usage)

Use a YAML config to keep runs reproducible and override any value via CLI:

```bash
# Base run using YAML
uv run scripts/train.py --config configs/sft.yaml

# Override a few knobs at the CLI
uv run scripts/train.py --config configs/sft.yaml \
  --epochs 3 \
  --learning-rate 1e-4 \
  --lora-r 8

# Resume from a prior checkpoint
uv run scripts/train.py --config configs/sft.yaml \
  --resume-from-checkpoint runs/sft_mistral_lora/checkpoint-500
```

Notes:

- YAML keys map directly to CLI flags (flat mapping).
- CLI overrides always take precedence over YAML defaults.
- See `configs/sft.yaml` for a complete example.

## 📊 Evaluation

- Scripts in `eval/` reproduce metrics.
- Results saved to `results/` as CSV/JSON, summarized in README tables.

## 🧪 Tests

```bash
uv run pytest -q
```

## 📦 Packaging (Task #15)

Use the packaging utility to export either a PEFT adapter-only bundle or a merged-weights model suitable for standalone deployment.

```bash
# Adapter-only (copies adapter files and optional tokenizer)
uv run scripts/package_model.py \
  --base-model mistralai/Mistral-7B-Instruct-v0.3 \
  --adapter-dir runs/sft_mistral_lora/checkpoint-500 \
  --output-dir packages/mistral_sft_adapter \
  --include-tokenizer

# Merged weights (applies LoRA and saves full model)
uv run scripts/package_model.py \
  --base-model mistralai/Mistral-7B-Instruct-v0.3 \
  --adapter-dir runs/sft_mistral_lora/checkpoint-500 \
  --output-dir packages/mistral_sft_merged \
  --mode merged \
  --include-tokenizer
```

Outputs include a `package_info.json` with metadata. Tokenizer files are saved under `tokenizer/` when `--include-tokenizer` is provided.

## 📦 Structure

```text
llm-finetune-supportbot/
  ├─ src/
  ├─ api/
  ├─ demo.py
  ├─ eval/
  ├─ scripts/
  │   └─ package_model.py
  ├─ results/
  ├─ tests/
  ├─ pyproject.toml
  └─ README.md
```

## 🧩 Managing Dependencies

- Add runtime dep: `uv add fastapi`
- Add dev dep: `uv add --dev ruff`
- Sync env (incl. dev): `uv sync --dev`

## 📸 Demos

- CLI Q&A
- FastAPI endpoint (see `api/README.md`)
- Before/after qualitative examples

## 🗺️ Roadmap

- [ ] Define baseline & target metrics
- [ ] Implement MVP
- [ ] Add CI checks
- [ ] Document limitations & next steps

## ⚖️ License

MIT (adjust as needed). Respect upstream licenses.
