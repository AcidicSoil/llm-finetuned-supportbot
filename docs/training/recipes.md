# Training Recipes: SFT vs DPO

This project supports two training recipes via a single entrypoint `scripts/train.py` (alias to `train_lora.py`).

## Presets (precision & accumulation)

For quick ergonomics across common setups, you can apply a small YAML overlay, then still override anything via your main `--config` or CLI flags. Presets live in `configs/presets/`.

### Tests for Presets

- Location: `tests/unit/test_presets.py`
- What they cover:
  - `gpu-fp16` preset enables `--fp16` (and not `--bf16`).
  - `cpu` preset disables AMP and sets `--gradient-accumulation-steps=1`.
  - `memory-efficient` preset increases `--gradient-accumulation-steps` to 8.
  - Precedence order is enforced as: base defaults < preset < `--config` < CLI.

How to run only these tests:

```bash
uv run pytest -q tests/unit/test_presets.py
```

Windows (without `uv`):

```powershell
.\.venv\Scripts\python -m pytest -q tests\unit\test_presets.py
```

- `cpu`: disables AMP (`bf16: false`, `fp16: false`), `gradient_accumulation_steps: 1`.
- `gpu-bf16`: enables `bf16`, disables `fp16`.
- `gpu-fp16`: enables `fp16`, disables `bf16`.
- `memory-efficient`: keeps per-device batch size small and increases `gradient_accumulation_steps: 8`.

Usage examples:

```
python scripts/train.py \
  --preset gpu-bf16 \
  --config configs/sft.yaml

# Preset + explicit override (CLI wins):
python scripts/train.py --preset gpu-fp16 --bf16 --config configs/sft.yaml

# Memory-friendly accumulation overlay (precision inherits from config/CLI):
python scripts/train.py --preset memory-efficient --config configs/sft.yaml
```

Precedence: project defaults < preset < `--config` file < explicit CLI flags.

Optional: add `--auto-precision` to prefer bf16 automatically on supported NVIDIA GPUs when neither `--bf16` nor `--fp16` is provided.

- SFT (Supervised Fine-Tuning) — learn from prompt→completion pairs.
- DPO (Direct Preference Optimization) — learn from preference pairs (chosen vs. rejected).

## Common Setup

- Use YAML configs to pin defaults, and override any key at the CLI.
- Quantization: `--quant {4bit,8bit,none}`; LoRA targets default to `auto` and are inferred per model.

```bash
# SFT quickstart
uv run scripts/train.py --config configs/sft.yaml

# DPO quickstart
uv run scripts/train.py --config configs/dpo.yaml \
  --splits-dir ./data/splits \
  --output-dir ./results/dpo-out
```

## SFT Data Expectations

Provide split files under `--splits-dir`:

- `train.jsonl`
- `val.jsonl`

Each line is a JSON object matching the DataRecord schema (see SCHEMA.md). The trainer converts records into prompt+completion pairs internally.

## DPO Data Expectations

Provide preference files under `--splits-dir` (or pass explicit paths with `--dpo-train-file/--dpo-val-file`):

- `train.dpo.jsonl`
- `val.dpo.jsonl`

Each line must be an object with string fields `{ "prompt", "chosen", "rejected" }`.

Example:

```json
{"prompt": "Hello?", "chosen": "Hi!", "rejected": "Goodbye."}
```

The helper `load_preference_jsonl()` in `src/parsers/preference.py` validates and converts JSONL into a `datasets.Dataset` with columns `[prompt, chosen, rejected]` expected by TRL.

## Key Configs

- SFT: see `configs/sft.yaml`
- DPO: see `configs/dpo.yaml`
  - `beta`: temperature-like parameter for the DPO loss
  - `max_length`: maximum combined sequence length
  - `max_prompt_length`: maximum prompt length

## Notes

- Reference model: some TRL versions require a frozen reference model. The trainer creates one automatically when needed.
- Best-model selection: you may enable `--load-best-model-at-end` with metric knobs; support varies across TRL versions.
- Smoke tests: tiny runs exist for both SFT and DPO under `tests/smoke/`.
