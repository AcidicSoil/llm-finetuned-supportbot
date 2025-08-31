# Fine-tune a Small LLM on Support Data

[![llm-finetune-supportbot](https://github.com/AcidicSoil/llm-finetuned-supportbot/actions/workflows/ci.yml/badge.svg)](https://github.com/AcidicSoil/llm-finetuned-supportbot/actions/workflows/ci.yml)

**Repo:** `llm-finetune-supportbot` • **Last Updated:** 2025-08-19

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

## 📦 Structure

```text
llm-finetune-supportbot/
  ├─ src/
  ├─ demo.py
  ├─ eval/
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
- FastAPI endpoint
- Before/after qualitative examples

## 🗺️ Roadmap

- [ ] Define baseline & target metrics
- [ ] Implement MVP
- [ ] Add CI checks
- [ ] Document limitations & next steps

## ⚖️ License

MIT (adjust as needed). Respect upstream licenses.
