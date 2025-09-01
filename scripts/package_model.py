#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel


def _json_dump(obj: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True)


def _copy_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Package trained model artifacts for deployment")
    p.add_argument("--base-model", required=True, help="Base HF model id or local path")
    p.add_argument("--adapter-dir", required=True, type=Path, help="Directory containing trained PEFT adapter (trainer.save_model output)")
    p.add_argument("--output-dir", required=True, type=Path, help="Destination directory for the packaged artifacts")
    p.add_argument("--mode", choices=["adapter", "merged"], default="adapter", help="Export mode: adapter (default) or merged full weights")
    p.add_argument("--include-tokenizer", action="store_true", help="Also save tokenizer alongside package")
    p.add_argument("--adapter-name", default="default", help="Adapter name if non-default (for informational metadata)")
    return p.parse_args()


def package_adapter_only(base_model: str, adapter_dir: Path, output_dir: Path, include_tokenizer: bool, adapter_name: str) -> None:
    out_adapter = output_dir / "adapter"
    _copy_tree(adapter_dir, out_adapter)

    meta = {
        "package_type": "peft-adapter",
        "base_model": base_model,
        "adapter_name": adapter_name,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "library_versions": {
            "transformers": __import__("transformers").__version__,
            "peft": __import__("peft").__version__,
            "torch": torch.__version__,
        },
    }
    _json_dump(meta, output_dir / "package_info.json")

    if include_tokenizer:
        tok = AutoTokenizer.from_pretrained(base_model, use_fast=True)
        tok.save_pretrained(output_dir / "tokenizer")


def package_merged(base_model: str, adapter_dir: Path, output_dir: Path, include_tokenizer: bool) -> None:
    # Load base, attach adapter, merge and save full model
    base = AutoModelForCausalLM.from_pretrained(base_model, torch_dtype="auto", device_map="auto")
    model = PeftModel.from_pretrained(base, str(adapter_dir))
    merged = model.merge_and_unload()
    (output_dir / "model").mkdir(parents=True, exist_ok=True)
    merged.save_pretrained(output_dir / "model")

    meta = {
        "package_type": "merged-weights",
        "base_model": base_model,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "library_versions": {
            "transformers": __import__("transformers").__version__,
            "peft": __import__("peft").__version__,
            "torch": torch.__version__,
        },
    }
    _json_dump(meta, output_dir / "package_info.json")

    if include_tokenizer:
        tok = AutoTokenizer.from_pretrained(base_model, use_fast=True)
        tok.save_pretrained(output_dir / "tokenizer")


def main() -> None:
    args = parse_args()
    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.mode == "adapter":
        package_adapter_only(args.base_model, args.adapter_dir, output_dir, args.include_tokenizer, args.adapter_name)
    else:
        package_merged(args.base_model, args.adapter_dir, output_dir, args.include_tokenizer)

    print(f"[package_model] Wrote package to: {output_dir}")


if __name__ == "__main__":
    main()

