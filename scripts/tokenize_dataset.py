from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List

from src.models import DataRecord
from src.parsers import load_json_records, load_jsonl_records, load_csv_records
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
    p = argparse.ArgumentParser(description="Tokenize dataset into prompt/answer token ids")
    p.add_argument("input", type=Path, help="Input dataset path (.jsonl/.json/.csv)")
    p.add_argument("output", type=Path, help="Output JSONL path with token ids")
    p.add_argument("--model", required=True, help="HF model id for tokenizer (e.g., 'bert-base-uncased')")
    p.add_argument("--max-length", type=int, default=512)
    p.add_argument("--padding", default="max_length", choices=["True", "False", "max_length", "longest"], help="Padding strategy")
    p.add_argument("--truncation", default="True", choices=["True", "False", "longest_first", "only_first", "only_second"], help="Truncation strategy")
    args = p.parse_args()

    # Normalize boolean-like strings
    padding = True if args.padding == "True" else False if args.padding == "False" else args.padding
    truncation = True if args.truncation == "True" else False if args.truncation == "False" else args.truncation

    records = _load(args.input)
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


if __name__ == "__main__":
    main()

