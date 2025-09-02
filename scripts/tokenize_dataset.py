from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List

from src import tokenization as tokmod
from src.chunking import chunk_ids_sliding_window
from src.models import DataRecord
from src.parsers import load_csv_records, load_json_records, load_jsonl_records
from src.tokenization import tokenize_pairs


def _load(path: Path) -> List[DataRecord]:
    sfx = path.suffix.lower()
    if sfx in {".jsonl", ".ndjson"}:
        return load_jsonl_records(str(path))
    if sfx == ".json":
        return load_json_records(str(path))
    if sfx == ".csv":
        return load_csv_records(str(path))
    raise SystemExit(f"unsupported input format: {sfx}")


def main() -> None:
    p = argparse.ArgumentParser(
        description="Tokenize dataset into prompt/answer token ids"
    )
    p.add_argument("input", type=Path, help="Input dataset path (.jsonl/.json/.csv)")
    p.add_argument("output", type=Path, help="Output JSONL path with token ids")
    p.add_argument(
        "--model",
        required=True,
        help="HF model id for tokenizer (e.g., 'bert-base-uncased')",
    )
    p.add_argument("--max-length", type=int, default=512)
    p.add_argument(
        "--padding",
        default="max_length",
        choices=["True", "False", "max_length", "longest"],
        help="Padding strategy",
    )
    p.add_argument(
        "--truncation",
        default="True",
        choices=["True", "False", "longest_first", "only_first", "only_second"],
        help="Truncation strategy",
    )
    p.add_argument(
        "--chunking-strategy",
        default="truncate",
        choices=["truncate", "sliding_window"],
        help="Handle over-length inputs by truncation (default) or sliding window",
    )
    p.add_argument(
        "--stride",
        type=int,
        default=128,
        help="Overlap size when using sliding_window",
    )
    args = p.parse_args()

    # Normalize boolean-like strings
    padding = (
        True
        if args.padding == "True"
        else False if args.padding == "False" else args.padding
    )
    truncation = (
        True
        if args.truncation == "True"
        else False if args.truncation == "False" else args.truncation
    )

    records = _load(args.input)

    if args.chunking_strategy == "truncate":
        toks = tokenize_pairs(
            records,
            args.model,
            max_length=args.max_length,
            padding=padding,  # type cast at runtime by HF
            truncation=truncation,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", encoding="utf-8", newline="\n") as f:
            for i, rec in enumerate(records):
                row = {
                    "id": rec.id,
                    "prompt_input_ids": toks.prompt_input_ids[i],
                    "prompt_attention_mask": toks.prompt_attention_mask[i],
                    "answer_input_ids": toks.answer_input_ids[i],
                    "answer_attention_mask": toks.answer_attention_mask[i],
                }
                f.write(json.dumps(row, ensure_ascii=False))
                f.write("\n")
        return

    # sliding_window path: produce multiple rows per record as needed
    tok = tokmod._ensure_tokenizer(args.model)  # reuse lazy-loading helper
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as f:
        for rec in records:
            # Compose text pairs
            from src.tokenization import default_pair_template

            prompt_text, answer_text = default_pair_template(rec)
            enc_p = tok(
                [prompt_text], padding=False, truncation=False, return_tensors=None
            )
            enc_a = tok(
                [answer_text], padding=False, truncation=False, return_tensors=None
            )
            prompt_ids = list(enc_p["input_ids"][0])
            answer_ids = list(enc_a["input_ids"][0])
            # Window both sides independently
            p_chunks, p_masks = chunk_ids_sliding_window(
                prompt_ids, max_length=args.max_length, stride=args.stride, pad_id=tok.pad_token_id or 0  # type: ignore[attr-defined]
            )
            a_chunks, a_masks = chunk_ids_sliding_window(
                answer_ids, max_length=args.max_length, stride=args.stride, pad_id=tok.pad_token_id or 0  # type: ignore[attr-defined]
            )
            # Emit rows per-chunk, aligning counts by max of both (repeat last when shorter)
            n = max(len(p_chunks), len(a_chunks))
            for i in range(n):
                row = {
                    "id": f"{rec.id}#chunk{i+1}",
                    "prompt_input_ids": p_chunks[min(i, len(p_chunks) - 1)],
                    "prompt_attention_mask": p_masks[min(i, len(p_masks) - 1)],
                    "answer_input_ids": a_chunks[min(i, len(a_chunks) - 1)],
                    "answer_attention_mask": a_masks[min(i, len(a_masks) - 1)],
                }
                f.write(json.dumps(row, ensure_ascii=False))
                f.write("\n")


if __name__ == "__main__":
    main()
