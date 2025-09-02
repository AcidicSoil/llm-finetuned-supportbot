# Error Analysis & Evaluation Suites

## Heuristic Error Annotation

Enable optional error annotation during evaluation to tag responses with coarse error types:

```bash
uv run scripts/eval.py \
  --base_model_name sshleifer/tiny-gpt2 \
  --peft_model_path ./runs/adapter \
  --evaluation_suite eval/suites/support_billing.jsonl \
  --output_dir results/eval_billing \
  --annotate_errors
```

This adds an `error_type` column (when PEFT results are present) and saves aggregate rates to `error_stats.json`.

Error types (heuristic):
- `refusal` — detects generic refusal phrasing.
- `style` — flags overly terse responses.
- `hallucination` — placeholder (needs references; not auto-detected here).
- `other` — fallback.

Implementation: see `src/eval_schema.py`.

## Evaluation Suites

Two starter suites are provided under `eval/suites/`:
- `support_billing.jsonl` — billing/refunds/invoicing scenarios
- `support_setup.jsonl` — setup/configuration/troubleshooting scenarios

Each line is `{ "prompt": "..." }`.

