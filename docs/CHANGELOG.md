# Changelog

All notable changes to this project will be documented in this file.

## 2025-09-02 — Task #19: Add Configurable Training Recipes (SFT/DPO)

- Added preference dataset loader: `src/parsers/preference.py` with `load_preference_jsonl()`.
- Extended training entry `scripts/train_lora.py` with `--recipe {sft,dpo}` and DPO options (`--beta`, `--max-length`, `--max-prompt-length`, `--dpo-train-file`, `--dpo-val-file`).
- New config `configs/dpo.yaml` with minimal, runnable defaults.
- New smoke test `tests/smoke/test_dpo_smoke.py` for a tiny DPO step.
- README updated with DPO usage instructions.

Breaking changes: none. The SFT path and existing flags remain backward compatible.
