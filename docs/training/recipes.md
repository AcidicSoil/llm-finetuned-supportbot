# Training Recipes: SFT vs DPO

This project supports two training recipes via a single entrypoint `scripts/train.py` (alias to `train_lora.py`).

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

