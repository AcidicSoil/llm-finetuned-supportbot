from __future__ import annotations

"""
Master data preparation script.

Pipeline:
1) Load raw records (.jsonl/.json/.csv)
2) Validate dataset (schema + simple PII + tag vocab optional)
3) Deterministic split into train/val/test
4) Tokenize each split with an HF tokenizer
5) Write outputs under the specified output directory

Outputs:
- <out_dir>/splits/{train,val,test}.jsonl          # raw DataRecord JSONL
- <out_dir>/tokenized/{train,val,test}.jsonl       # token ids per split
"""

import argparse
import json
from pathlib import Path
from typing import List, Sequence

from src.models import DataRecord, validate_dataset
from src.parsers import (
    load_csv_records,
    load_json_records,
    load_jsonl_records,
)
from src.split import split_records
from src.tokenization import tokenize_pairs


def _load_any(path: Path) -> List[DataRecord]:
    sfx = path.suffix.lower()
    if sfx in {".jsonl", ".ndjson"}:
        return load_jsonl_records(str(path))
    if sfx == ".json":
        return load_json_records(str(path))
    if sfx == ".csv":
        return load_csv_records(str(path))
    raise SystemExit(f"unsupported input format: {sfx}")


def _dump_jsonl_records(records: Sequence[DataRecord], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="\n") as f:
        for r in records:
            f.write(r.model_dump_json(ensure_ascii=False))
            f.write("\n")


def _dump_tokenized(
    records: Sequence[DataRecord],
    model_id: str,
    out_path: Path,
    *,
    max_length: int,
    padding: str | bool,
    truncation: str | bool,
) -> None:
    toks = tokenize_pairs(
        list(records),
        model_id,
        max_length=max_length,
        padding=padding,
        truncation=truncation,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="\n") as f:
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


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Orchestrate data ingestion, validation, split, and tokenization"
    )
    p.add_argument("input", type=Path, help="Input dataset path (.jsonl/.json/.csv)")
    p.add_argument("output_dir", type=Path, help="Output directory for processed data")

    # Validation
    p.add_argument(
        "--allowed-tags",
        nargs="*",
        default=None,
        help="Optional whitelist of allowed tag values; any other tags cause validation failure",
    )
    p.add_argument(
        "--allow-validation-warnings",
        action="store_true",
        help="Do not exit on validation issues; print and continue",
    )

    # Split
    p.add_argument("--train", type=float, default=0.8, help="Train ratio (default 0.8)")
    p.add_argument(
        "--val", type=float, default=0.1, help="Validation ratio (default 0.1)"
    )
    p.add_argument("--test", type=float, default=0.1, help="Test ratio (default 0.1)")
    p.add_argument(
        "--stratify-by",
        type=str,
        default="source",
        choices=["none", "source", "primary_tag"],
        help="Stratify key (default: source)",
    )
    p.add_argument(
        "--seed", type=int, default=42, help="Deterministic seed (default 42)"
    )

    # Tokenization
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
        help="Padding strategy per HF tokenizers",
    )
    p.add_argument(
        "--truncation",
        default="True",
        choices=["True", "False", "longest_first", "only_first", "only_second"],
        help="Truncation strategy per HF tokenizers",
    )

    return p.parse_args()


def main() -> None:
    args = parse_args()

    # Normalize boolean-like strings to bool for HF API where allowed
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

    print("[prepare_data] Loading records…")
    records = _load_any(args.input)
    print(f"[prepare_data] Loaded {len(records)} records from {args.input}")

    print("[prepare_data] Validating dataset…")
    ok, issues = validate_dataset(records, allowed_tags=args.allowed_tags)
    if not ok:
        print("[prepare_data] Validation issues detected:")
        for msg in issues:
            print(f" - {msg}")
        if not args.allow_validation_warnings:
            raise SystemExit(1)
    else:
        print("[prepare_data] Validation OK")

    print("[prepare_data] Splitting dataset…")
    splits = split_records(
        records,
        train_ratio=args.train,
        val_ratio=args.val,
        test_ratio=args.test,
        seed=args.seed,
        stratify_by=args.stratify_by,  # type: ignore[arg-type]
    )
    out_dir = args.output_dir
    raw_dir = out_dir / "splits"
    tok_dir = out_dir / "tokenized"

    print(f"[prepare_data] Writing raw splits to {raw_dir}")
    _dump_jsonl_records(splits.train, raw_dir / "train.jsonl")
    _dump_jsonl_records(splits.val, raw_dir / "val.jsonl")
    _dump_jsonl_records(splits.test, raw_dir / "test.jsonl")

    print(f"[prepare_data] Tokenizing splits with tokenizer '{args.model}'…")
    _dump_tokenized(
        splits.train,
        args.model,
        tok_dir / "train.jsonl",
        max_length=args.max_length,
        padding=padding,
        truncation=truncation,
    )
    _dump_tokenized(
        splits.val,
        args.model,
        tok_dir / "val.jsonl",
        max_length=args.max_length,
        padding=padding,
        truncation=truncation,
    )
    _dump_tokenized(
        splits.test,
        args.model,
        tok_dir / "test.jsonl",
        max_length=args.max_length,
        padding=padding,
        truncation=truncation,
    )

    print("[prepare_data] Done.")


if __name__ == "__main__":
    main()
