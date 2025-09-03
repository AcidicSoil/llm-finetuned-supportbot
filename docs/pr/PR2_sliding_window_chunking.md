# feat(tokenization): Advanced input length handling (sliding window)

## Summary
Add optional sliding-window chunking to reduce truncation artifacts for over-length inputs.

- New: `src/chunking.py` with sliding-window utility and masks.
- Preprocessing: `scripts/tokenize_dataset.py` gets `--chunking-strategy` and `--stride`.
- Inference (CLI): `demo.py` can feed the last window.
- Config: `configs/{sft,dpo}.yaml` include a `chunking` block.
- Tests: `tests/test_chunking.py` validates windows/masks/edge cases.
- Docs: README section with usage examples.

Defaults remain unchanged (truncate).

## Motivation
Truncating long contexts can hurt quality. Sliding windows let us: (a) train on full content via overlapping chunks, (b) during inference, keep the most recent context window.

## How It Works

- Window bounds: `step = max(max_length - stride, 1)`; always include tail window.
- Output: padded chunks (length = `max_length`) with 1/0 attention masks.
- Preprocessing: emits multiple rows per record when needed (`id#chunkN`).
- Inference: last-window helper feeds only the most recent `max_length` tokens.

## Usage

```bash
# Preprocessing (multi-chunk)
uv run scripts/tokenize_dataset.py data/raw.jsonl data/tok.jsonl \
  --model mistralai/Mistral-7B-Instruct-v0.3 \
  --max-length 512 \
  --chunking-strategy sliding_window \
  --stride 128

# Demo (last-window inference)
uv run demo.py \
  --base_model_name mistralai/Mistral-7B-Instruct-v0.3 \
  --chunking-strategy sliding_window \
  --max-input-length 512 \
  --stride 128
```

## Test Logs (offline)

```text
$ export HF_HUB_OFFLINE=1
$ uv run pytest -q
...  (unit tests pass; smoke tests are skipped when offline) ...
```

## Compatibility & Risk

- Backward compatible: default strategy is still `truncate`.
- Opt-in behavior with clear flags and YAML config.

## Checklist

- [x] Unit tests cover window math and masks
- [x] README updated with examples
- [x] CI passes
