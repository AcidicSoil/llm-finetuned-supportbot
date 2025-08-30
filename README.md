# Fine-tune a Small LLM on Support Data

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
