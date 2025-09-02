from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List

from src.models import DataRecord
from src.parsers import load_csv_records, load_json_records, load_jsonl_records
from src.split import split_records


def _load(path: Path) -> List[DataRecord]:
    suffix = path.suffix.lower()
    if suffix == ".jsonl" or suffix == ".ndjson":
        return load_jsonl_records(str(path))
    if suffix == ".json":
        return load_json_records(str(path))
    if suffix == ".csv":
        return load_csv_records(str(path))
    raise SystemExit(f"unsupported input format: {suffix}")


def _dump_jsonl(records: List[DataRecord], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="\n") as f:
        for r in records:
            f.write(r.model_dump_json(ensure_ascii=False))
            f.write("\n")


def main() -> None:
    p = argparse.ArgumentParser(description="Deterministic stratified dataset split")
    p.add_argument("input", type=Path, help="Path to input dataset (.jsonl/.json/.csv)")
    p.add_argument(
        "output_dir", type=Path, help="Directory to write train/val/test JSONL files"
    )
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
    args = p.parse_args()

    records = _load(args.input)
    result = split_records(
        records,
        train_ratio=args.train,
        val_ratio=args.val,
        test_ratio=args.test,
        seed=args.seed,
        stratify_by=args.stratify_by,  # type: ignore[arg-type]
    )

    _dump_jsonl(result.train, args.output_dir / "train.jsonl")
    _dump_jsonl(result.val, args.output_dir / "val.jsonl")
    _dump_jsonl(result.test, args.output_dir / "test.jsonl")

    stats = {
        "counts": {
            "train": len(result.train),
            "val": len(result.val),
            "test": len(result.test),
        }
    }
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
