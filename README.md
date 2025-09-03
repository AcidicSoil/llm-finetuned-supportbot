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

# Save best checkpoint based on eval metric (Task #20)
uv run scripts/train.py --config configs/sft.yaml \
  --load-best-model-at-end \
  --metric-name eval_loss \
  --no-greater-is-better
```

### DPO (Preference Training)

Provide a DPO config and preference JSONL files with lines shaped as `{"prompt": ..., "chosen": ..., "rejected": ...}`. By default, the trainer looks for `train.dpo.jsonl` and `val.dpo.jsonl` under `--splits-dir`. You can also point to explicit files with `--dpo-train-file/--dpo-val-file`.

```bash
uv run scripts/train.py --config configs/dpo.yaml \
  --splits-dir ./data/splits \
  --output-dir ./results/dpo-out
```

Key knobs: `beta`, `max_length`, `max_prompt_length` in `configs/dpo.yaml`.

More details and examples: see `docs/training/recipes.md`.

### Advanced Input Length Handling (Task #22)

Two strategies are supported for over-length inputs:

- Truncate (default): cut to `max_length`.
- Sliding window: create overlapping chunks using `stride`.

Configure in YAML (applies to preprocessing utilities):

```yaml
chunking:
  strategy: truncate        # or: sliding_window
  max_seq_length: 512
  stride: 128
```

Tokenize a dataset with sliding windows:

```bash
uv run scripts/tokenize_dataset.py \
  data/raw/dataset.jsonl \
  data/tokenized/out.jsonl \
  --model mistralai/Mistral-7B-Instruct-v0.3 \
  --max-length 512 \
  --chunking-strategy sliding_window \
  --stride 128
```

Interactive demo with windowing at inference:

```bash
uv run demo.py \
  --base_model_name mistralai/Mistral-7B-Instruct-v0.3 \
  --chunking-strategy sliding_window \
  --max-input-length 512 \
  --stride 128
```

### Best Model Selection

You can enable automatic best-checkpoint selection (both SFT and DPO paths) by adding:

```bash
--load-best-model-at-end \
--metric-name eval_loss \
--no-greater-is-better
```

These flags are already supported by the trainer config. When enabled, the trainer loads the best-performing checkpoint (per metric) before `save_model()`.

Notes:

- YAML keys map directly to CLI flags (flat mapping).
- CLI overrides always take precedence over YAML defaults.
- See `configs/sft.yaml` for a complete example.
- Best-model selection: use `--load-best-model-at-end` with `--metric-name` and
  `--greater-is-better/--no-greater-is-better` to control how the best checkpoint
  is chosen (defaults target minimizing `eval_loss`).
- LoRA target inference: `--lora-target-modules auto` (default) detects sensible
  targets for common architectures (e.g., GPT-2 uses `c_attn,c_fc,c_proj`; LLaMA/Mistral
  uses `q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj`). Override to force.

## 📊 Evaluation

- Scripts in `eval/` reproduce metrics.
- Results saved to `results/` as CSV/JSON, summarized in README tables.
- Optional error annotation and starter suites documented in `docs/eval/error_analysis.md`.

## 🧪 Tests

Local testing works both fully offline (unit tests) and online (optional smoke tests with a tiny model).

- macOS/Linux (bash/zsh)
  - Offline full suite (skips smoke):

    ```bash
    export HF_HUB_OFFLINE=1
    uv run pytest -q
    ```

  - Online smoke only (pulls a tiny model):

    ```bash
    export HF_HUB_OFFLINE=0
    export TEST_TINY_MODEL_ID=sshleifer/tiny-gpt2
    uv run pytest -q -m smoke tests/smoke
    ```

- Windows (PowerShell)
  - Activate venv: `..\.venv\Scripts\Activate.ps1`
  - Offline full suite (skips smoke):

    ```powershell
    $env:HF_HUB_OFFLINE = '1'
    .\.venv\Scripts\python -m pytest -q
    ```

  - Online smoke only (pulls a tiny model):

    ```powershell
    $env:HF_HUB_OFFLINE = '0'
    $env:TEST_TINY_MODEL_ID = 'sshleifer/tiny-gpt2'
    .\.venv\Scripts\python -m pytest -q -m smoke tests\smoke
    ```

Notes

- Smoke tests require internet access and download a tiny checkpoint; they are skipped when `HF_HUB_OFFLINE=1`.
- If pytest warns about an unknown `smoke` marker, you can register it by adding to `pyproject.toml`:

  ```toml
  [tool.pytest.ini_options]
  markers = [
    "smoke: tiny online tests"
  ]
  ```

Additional smoke:

- DPO path: `tests/smoke/test_dpo_smoke.py` runs a tiny preference step using `--recipe dpo`.

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
