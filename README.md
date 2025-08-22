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
# 1) Create and activate env
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2) Install
pip install -r requirements.txt

# 3) Run demo
python demo.py
```

## 📊 Evaluation

- Scripts in `eval/` reproduce metrics.
- Results saved to `results/` as CSV/JSON, summarized in README tables.

## 🧪 Tests

```bash
pytest -q
```

## 📦 Structure

```text
llm-finetune-supportbot/
  ├─ src/
  ├─ demo.py
  ├─ eval/
  ├─ results/
  ├─ tests/
  ├─ requirements.txt
  └─ README.md
```

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
