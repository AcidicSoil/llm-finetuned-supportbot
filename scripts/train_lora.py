from __future__ import annotations

"""
LoRA SFT training script with bitsandbytes quantization.

Features
- Loads raw split JSONL produced by scripts/prepare_data.py (train/val)
- Formats each record into prompt + completion for TRL SFTTrainer
- Loads base model with 4-bit/8-bit quantization (bitsandbytes)
- Applies PEFT LoRA adapters (configurable target modules)
- Deterministic seeds and checkpointing
- Resume-from-checkpoint support
"""

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple, Any, Dict

import torch
from datasets import Dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    set_seed,
)
from trl import SFTConfig, SFTTrainer
from peft import LoraConfig, TaskType, get_peft_model
import yaml

from src.models import DataRecord
from src.parsers import load_jsonl_records
from src.tokenization import default_pair_template


def _load_split_jsonl(path: Path) -> List[DataRecord]:
    return load_jsonl_records(str(path))


def _records_to_prompt_completion(records: Iterable[DataRecord]) -> Dataset:
    prompts: List[str] = []
    completions: List[str] = []
    for rec in records:
        p, a = default_pair_template(rec)
        prompts.append(p)
        completions.append(a)
    return Dataset.from_dict({"prompt": prompts, "completion": completions})


def _bitsandbytes_config(quant: str, *, compute_dtype: str, quant_type: str, double_quant: bool) -> BitsAndBytesConfig | None:
    if quant not in {"4bit", "8bit", "none"}:
        raise SystemExit("--quant must be one of: 4bit, 8bit, none")
    if quant == "none":
        return None
    # Map dtype string to torch dtype
    dtype_map = {
        "float32": torch.float32,
        "float16": torch.float16,
        "bfloat16": torch.bfloat16,
    }
    bnb_compute_dtype = dtype_map.get(compute_dtype.lower())
    if quant == "8bit":
        return BitsAndBytesConfig(load_in_8bit=True)
    # 4bit
    return BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type=quant_type,
        bnb_4bit_compute_dtype=bnb_compute_dtype,
        bnb_4bit_use_double_quant=bool(double_quant),
    )


def _default_lora_targets() -> List[str]:
    # Common projections for LLaMA/Mistral-style blocks; configurable via CLI
    return [
        "q_proj",
        "k_proj",
        "v_proj",
        "o_proj",
        "gate_proj",
        "up_proj",
        "down_proj",
    ]


def parse_args() -> argparse.Namespace:
    """Parse CLI args with optional YAML config defaults.

    Flow:
    1) Parse once to detect --config
    2) If provided, load YAML and set as parser defaults
    3) Parse again so explicit CLI flags override YAML
    """
    p = argparse.ArgumentParser(description="LoRA SFT training with quantization")
    # Config file (YAML) support
    p.add_argument("--config", type=Path, default=None, help="Path to YAML config with training params")
    p.add_argument("--model", required=True, help="Base HF model id (e.g., 'mistralai/Mistral-7B-Instruct-v0.3')")
    p.add_argument("--splits-dir", type=Path, required=True, help="Directory containing train.jsonl and val.jsonl (from prepare_data)")
    p.add_argument("--output-dir", type=Path, required=True, help="Training output directory for checkpoints")

    # Quantization
    p.add_argument("--quant", default="4bit", choices=["4bit", "8bit", "none"], help="Quantization mode (default: 4bit)")
    p.add_argument("--bnb-compute-dtype", default="bfloat16", choices=["float32", "float16", "bfloat16"], help="4-bit compute dtype")
    p.add_argument("--bnb-quant-type", default="nf4", choices=["nf4", "fp4"], help="4-bit quant type")
    p.add_argument("--bnb-double-quant", action="store_true", help="Enable 4-bit double quantization")

    # LoRA
    p.add_argument("--lora-r", type=int, default=16)
    p.add_argument("--lora-alpha", type=int, default=32)
    p.add_argument("--lora-dropout", type=float, default=0.05)
    p.add_argument(
        "--lora-target-modules",
        nargs="*",
        default=_default_lora_targets(),
        help="Target module names for LoRA (default: common proj layers)",
    )

    # Trainer
    p.add_argument("--epochs", type=int, default=1)
    p.add_argument("--per-device-train-batch-size", type=int, default=1)
    p.add_argument("--per-device-eval-batch-size", type=int, default=1)
    p.add_argument("--gradient-accumulation-steps", type=int, default=4)
    p.add_argument("--learning-rate", type=float, default=2e-5)
    p.add_argument("--logging-steps", type=int, default=10)
    p.add_argument("--save-steps", type=int, default=50)
    p.add_argument("--eval-steps", type=int, default=100)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--bf16", action="store_true", help="Enable bfloat16 mixed precision if supported")
    p.add_argument("--fp16", action="store_true", help="Enable float16 mixed precision if supported")

    # Resume support
    p.add_argument(
        "--resume-from-checkpoint",
        type=Path,
        default=None,
        help="Path to checkpoint dir to resume training from",
    )
    # First pass: get --config if present
    prelim, _ = p.parse_known_args()
    if prelim.config is not None:
        if not prelim.config.exists():
            raise SystemExit(f"config file not found: {prelim.config}")
        with open(prelim.config, "r", encoding="utf-8") as f:
            loaded: Dict[str, Any] = yaml.safe_load(f) or {}
        if not isinstance(loaded, dict):
            raise SystemExit("config file must parse to a mapping/dict")
        # Accept flat keys that match argparse dest names
        # Example keys: model, splits_dir, output_dir, quant, bnb_compute_dtype, lora_r, epochs, learning_rate, etc.
        # NOTE: CLI flags will override these defaults on the final parse.
        p.set_defaults(**loaded)

    args = p.parse_args()
    # Echo effective config for reproducibility
    try:
        # Serialize Path objects to str for printing
        snapshot = {
            k: (str(v) if isinstance(v, Path) else v)
            for k, v in vars(args).items()
            if k != "config"
        }
        print("[train_lora] Effective arguments:")
        print(json.dumps(snapshot, indent=2, sort_keys=True))
    except Exception:
        pass
    return args


def main() -> None:
    args = parse_args()

    set_seed(args.seed)

    train_path = args.splits_dir / "train.jsonl"
    val_path = args.splits_dir / "val.jsonl"
    if not train_path.exists():
        raise SystemExit(f"missing train split: {train_path}")
    if not val_path.exists():
        raise SystemExit(f"missing val split: {val_path}")

    print("[train_lora] Loading splits…")
    train_records = _load_split_jsonl(train_path)
    val_records = _load_split_jsonl(val_path)
    train_ds = _records_to_prompt_completion(train_records)
    eval_ds = _records_to_prompt_completion(val_records)
    print(f"[train_lora] Train: {len(train_ds)}  Val: {len(eval_ds)}")

    print("[train_lora] Loading tokenizer…")
    tokenizer = AutoTokenizer.from_pretrained(args.model, use_fast=True)
    if tokenizer.pad_token is None and tokenizer.eos_token is not None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    print("[train_lora] Configuring quantization…")
    bnb_cfg = _bitsandbytes_config(
        args.quant,
        compute_dtype=args.bnb_compute_dtype,
        quant_type=args.bnb_quant_type,
        double_quant=args.bnb_double_quant,
    )

    print("[train_lora] Loading base model…")
    if bnb_cfg is None:
        model = AutoModelForCausalLM.from_pretrained(args.model, device_map="auto", torch_dtype="auto")
    else:
        model = AutoModelForCausalLM.from_pretrained(
            args.model,
            device_map="auto",
            torch_dtype="auto",
            quantization_config=bnb_cfg,
        )

    # Apply LoRA via PEFT
    print("[train_lora] Applying LoRA adapters…")
    lora_cfg = LoraConfig(
        r=int(args.lora_r),
        lora_alpha=int(args.lora_alpha),
        lora_dropout=float(args.lora_dropout),
        target_modules=list(args.lora_target_modules),
        task_type=TaskType.CAUSAL_LM,
        bias="none",
    )
    model = get_peft_model(model, lora_cfg)
    # Optional: show trainable share
    try:
        model.print_trainable_parameters()
    except Exception:
        pass

    # SFT training args
    print("[train_lora] Preparing trainer…")
    training_args = SFTConfig(
        output_dir=str(args.output_dir),
        overwrite_output_dir=True,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.per_device_train_batch_size,
        per_device_eval_batch_size=args.per_device_eval_batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        learning_rate=args.learning_rate,
        logging_steps=args.logging_steps,
        save_strategy="steps",
        save_steps=args.save_steps,
        evaluation_strategy="steps",
        eval_steps=args.eval_steps,
        seed=args.seed,
        fp16=args.fp16,
        bf16=args.bf16,
        report_to=[],  # disable wandb/tensorboard by default
    )

    trainer = SFTTrainer(
        model=model,
        args=training_args,
        tokenizer=tokenizer,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        peft_config=lora_cfg,
    )

    print("[train_lora] Starting training…")
    trainer.train(resume_from_checkpoint=str(args.resume_from_checkpoint) if args.resume_from_checkpoint else None)
    print("[train_lora] Saving model…")
    trainer.save_model()
    print("[train_lora] Done.")


if __name__ == "__main__":
    main()
