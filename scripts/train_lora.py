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
from pathlib import Path
from typing import Any, Dict, Iterable, List

import torch
import yaml
from datasets import Dataset
from peft import LoraConfig, TaskType, get_peft_model
from src.models import DataRecord
from src.parsers import load_jsonl_records, load_preference_jsonl
from src.tokenization import default_pair_template
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    set_seed,
)
from trl import SFTConfig, SFTTrainer

# Repo root (for locating preset files regardless of CWD)
ROOT = Path(__file__).resolve().parent.parent


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


def _bitsandbytes_config(
    quant: str, *, compute_dtype: str, quant_type: str, double_quant: bool
) -> BitsAndBytesConfig | None:
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


def _infer_lora_targets_from_model(model) -> List[str]:
    """Infer sensible LoRA targets based on module names.

    - LLaMA/Mistral/Qwen2-style: q_proj/k_proj/v_proj/o_proj/gate_proj/up_proj/down_proj
    - GPT-2-style: c_attn/c_fc/c_proj
    - Falcon-style: query_key_value/dense_h_to_4h/dense_4h_to_h
    Fallback: return an empty list to let PEFT decide or error early.
    """
    names = [n for n, _ in model.named_modules()]
    if any(".c_attn" in n for n in names):
        return ["c_attn", "c_fc", "c_proj"]
    if any(".q_proj" in n for n in names):
        return [
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ]
    if any(".query_key_value" in n for n in names):
        return ["query_key_value", "dense_h_to_4h", "dense_4h_to_h"]
    return []


def parse_args() -> argparse.Namespace:
    """Parse CLI args with optional YAML config defaults.

    Flow:
    1) Parse once to detect --config
    2) If provided, load YAML and set as parser defaults
    3) Parse again so explicit CLI flags override YAML
    """
    p = argparse.ArgumentParser(description="LoRA SFT/DPO training with quantization")
    # Config file (YAML) support
    p.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to YAML config with training params",
    )
    # Optional preset overlay (applied before --config, still overridden by CLI flags)
    p.add_argument(
        "--preset",
        type=str,
        default=None,
        help=(
            "Name of preset overlay in configs/presets/<name>.yaml. Applied as defaults before --config and CLI."
        ),
    )
    # Mark as optional to allow programmatic/test invocation; we validate in main()
    p.add_argument(
        "--model",
        required=False,
        help="Base HF model id (e.g., 'mistralai/Mistral-7B-Instruct-v0.3')",
    )
    p.add_argument(
        "--splits-dir",
        type=Path,
        required=False,
        help="Directory containing train.jsonl and val.jsonl (from prepare_data)",
    )
    p.add_argument(
        "--output-dir",
        type=Path,
        required=False,
        help="Training output directory for checkpoints",
    )

    # Recipe selection
    p.add_argument(
        "--recipe",
        default="sft",
        choices=["sft", "dpo"],
        help="Training recipe: supervised (sft) or preference (dpo)",
    )
    # DPO-specific options
    p.add_argument("--beta", type=float, default=0.1, help="DPO beta parameter")
    p.add_argument(
        "--max-length", type=int, default=512, help="Max combined sequence length (DPO)"
    )
    p.add_argument(
        "--max-prompt-length", type=int, default=256, help="Max prompt length (DPO)"
    )
    p.add_argument(
        "--dpo-train-file",
        type=Path,
        default=None,
        help="Optional explicit path to DPO train JSONL {prompt,chosen,rejected}",
    )
    p.add_argument(
        "--dpo-val-file",
        type=Path,
        default=None,
        help="Optional explicit path to DPO val JSONL {prompt,chosen,rejected}",
    )

    # Quantization
    p.add_argument(
        "--quant",
        default="4bit",
        choices=["4bit", "8bit", "none"],
        help="Quantization mode (default: 4bit)",
    )
    p.add_argument(
        "--bnb-compute-dtype",
        default="bfloat16",
        choices=["float32", "float16", "bfloat16"],
        help="4-bit compute dtype",
    )
    p.add_argument(
        "--bnb-quant-type",
        default="nf4",
        choices=["nf4", "fp4"],
        help="4-bit quant type",
    )
    p.add_argument(
        "--bnb-double-quant",
        action="store_true",
        help="Enable 4-bit double quantization",
    )

    # LoRA
    p.add_argument("--lora-r", type=int, default=16)
    p.add_argument("--lora-alpha", type=int, default=32)
    p.add_argument("--lora-dropout", type=float, default=0.05)
    p.add_argument(
        "--lora-target-modules",
        nargs="*",
        default=["auto"],
        help="Target module names for LoRA; use 'auto' to infer based on model (default)",
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
    p.add_argument(
        "--bf16",
        action="store_true",
        help="Enable bfloat16 mixed precision if supported",
    )
    p.add_argument(
        "--fp16",
        action="store_true",
        help="Enable float16 mixed precision if supported",
    )
    # Optional: auto-detect precision when not explicitly set
    p.add_argument(
        "--auto-precision",
        action="store_true",
        help=(
            "If set and neither --bf16 nor --fp16 are provided, enables bf16 automatically on supported GPUs."
        ),
    )
    # Best model selection
    p.add_argument(
        "--load-best-model-at-end",
        dest="load_best_model_at_end",
        action="store_true",
        help="Load the best checkpoint (per metric) after training",
    )
    p.add_argument(
        "--metric-name",
        default="eval_loss",
        help="Metric name for best-model selection (default: eval_loss)",
    )
    p.add_argument(
        "--greater-is-better",
        dest="greater_is_better",
        action="store_true",
        help="Whether a higher metric value is better (default: False)",
    )
    p.add_argument(
        "--no-greater-is-better",
        dest="greater_is_better",
        action="store_false",
        help="Set greater_is_better to False (useful with eval_loss)",
    )
    p.set_defaults(greater_is_better=False)

    # Resume support
    p.add_argument(
        "--resume-from-checkpoint",
        type=Path,
        default=None,
        help="Path to checkpoint dir to resume training from",
    )
    # First pass: get --preset / --config if present
    prelim, _ = p.parse_known_args()
    # 1) Apply preset overlay, if any
    if getattr(prelim, "preset", None):
        preset_path = ROOT / "configs" / "presets" / f"{prelim.preset}.yaml"
        if not preset_path.exists():
            raise SystemExit(f"preset file not found: {preset_path}")
        try:
            with open(preset_path, "r", encoding="utf-8") as f:
                preset_loaded: Dict[str, Any] = yaml.safe_load(f) or {}
            if not isinstance(preset_loaded, dict):
                raise SystemExit(f"preset YAML must be a mapping: {preset_path}")
            p.set_defaults(**preset_loaded)
        except Exception as e:
            raise SystemExit(f"failed to load preset {preset_path}: {e}")
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

    # Use parse_known_args so test runners' flags (e.g., -q) don't break parsing
    args, _unknown = p.parse_known_args()

    # Enforce mutual exclusivity at parse-time based on explicit CLI flags.
    # This ensures CLI intent overrides preset/config defaults even when tests
    # call parse_args() without running main().
    try:
        import sys as _sys

        argv_tokens = set(_sys.argv[1:])
        bf16_set_explicit = "--bf16" in argv_tokens
        fp16_set_explicit = "--fp16" in argv_tokens
        if bf16_set_explicit and fp16_set_explicit:
            raise SystemExit("Both --bf16 and --fp16 were provided; choose one.")
        if bf16_set_explicit and not fp16_set_explicit:
            # User asked for bf16 explicitly; ensure fp16 is off
            args.fp16 = False
            args.bf16 = True
        if fp16_set_explicit and not bf16_set_explicit:
            # User asked for fp16 explicitly; ensure bf16 is off
            args.bf16 = False
            args.fp16 = True
    except Exception:
        # If sys.argv is not accessible or other issues, skip adjustment
        pass
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

    # Sanity: prevent both fp16 and bf16 simultaneously
    if getattr(args, "bf16", False) and getattr(args, "fp16", False):
        raise SystemExit("Both --bf16 and --fp16 were set; please choose only one.")

    # Optional precision auto-detect: only if user asked and neither flag set
    if getattr(args, "auto_precision", False) and not args.bf16 and not args.fp16:
        try:
            if torch.cuda.is_available():
                # Prefer bf16 on Ampere or newer if bf16 supported
                cap = torch.cuda.get_device_capability()
                bf16_supported = getattr(
                    torch.cuda, "is_bf16_supported", lambda: False
                )()
                if bf16_supported or (isinstance(cap, tuple) and cap >= (8, 0)):
                    args.bf16 = True
                    print("[train_lora] Auto-enabled bf16 based on GPU capability.")
        except Exception:
            pass

    # Validate required arguments when running as a CLI
    if not args.model or not args.splits_dir or not args.output_dir:
        raise SystemExit("--model, --splits-dir, and --output-dir are required")

    print("[train_lora] Loading splits…")
    if str(args.recipe).lower() == "dpo":
        # Resolve DPO files: explicit flags win; else look for train.dpo.jsonl/val.dpo.jsonl
        dpo_train = args.dpo_train_file or (args.splits_dir / "train.dpo.jsonl")
        dpo_val = args.dpo_val_file or (args.splits_dir / "val.dpo.jsonl")
        if not Path(dpo_train).exists():
            raise SystemExit(f"missing DPO train file: {dpo_train}")
        if not Path(dpo_val).exists():
            raise SystemExit(f"missing DPO val file: {dpo_val}")
        train_ds = load_preference_jsonl(dpo_train)
        eval_ds = load_preference_jsonl(dpo_val)
        print(f"[train_lora] DPO Train: {len(train_ds)}  Val: {len(eval_ds)}")
    else:
        train_path = args.splits_dir / "train.jsonl"
        val_path = args.splits_dir / "val.jsonl"
        if not train_path.exists():
            raise SystemExit(f"missing train split: {train_path}")
        if not val_path.exists():
            raise SystemExit(f"missing val split: {val_path}")

        train_records = _load_split_jsonl(train_path)
        val_records = _load_split_jsonl(val_path)
        train_ds = _records_to_prompt_completion(train_records)
        eval_ds = _records_to_prompt_completion(val_records)
        print(f"[train_lora] SFT Train: {len(train_ds)}  Val: {len(eval_ds)}")

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
        model = AutoModelForCausalLM.from_pretrained(
            args.model, device_map="auto", torch_dtype="auto"
        )
    else:
        model = AutoModelForCausalLM.from_pretrained(
            args.model,
            device_map="auto",
            torch_dtype="auto",
            quantization_config=bnb_cfg,
        )

    # Apply LoRA via PEFT
    print("[train_lora] Applying LoRA adapters…")
    # Determine targets
    targets = list(args.lora_target_modules)
    if (
        len(targets) == 1
        and isinstance(targets[0], str)
        and targets[0].lower() == "auto"
    ):
        targets = _infer_lora_targets_from_model(model)
        if not targets:
            raise SystemExit(
                "Could not infer LoRA target modules for this model; please pass --lora-target-modules …"
            )
        print(f"[train_lora] Inferred LoRA targets: {targets}")

    # Auto-adjust fan_in_fan_out for GPT-2 Conv1D blocks to avoid PEFT warning
    fan_in_fan_out = any(t in {"c_attn", "c_fc", "c_proj"} for t in targets)

    lora_cfg = LoraConfig(
        r=int(args.lora_r),
        lora_alpha=int(args.lora_alpha),
        lora_dropout=float(args.lora_dropout),
        target_modules=targets,
        task_type=TaskType.CAUSAL_LM,
        bias="none",
        fan_in_fan_out=fan_in_fan_out,
    )
    model = get_peft_model(model, lora_cfg)
    # Optional: show trainable share
    try:
        model.print_trainable_parameters()
    except Exception:
        pass

    # Build trainer & args depending on recipe
    print("[train_lora] Preparing trainer…")
    base_kwargs = {
        "output_dir": str(args.output_dir),
        "overwrite_output_dir": True,
        "num_train_epochs": args.epochs,
        "per_device_train_batch_size": args.per_device_train_batch_size,
        "per_device_eval_batch_size": args.per_device_eval_batch_size,
        "gradient_accumulation_steps": args.gradient_accumulation_steps,
        "learning_rate": args.learning_rate,
        "logging_steps": args.logging_steps,
        "save_strategy": "steps",
        "save_steps": args.save_steps,
        # evaluation/eval_steps vary across TRL versions
        "evaluation_strategy": "steps",
        "eval_steps": args.eval_steps,
        "seed": args.seed,
        "fp16": args.fp16,
        "bf16": args.bf16,
        "report_to": [],
        # Silence pin_memory warning on CPU-only runs
        "dataloader_pin_memory": bool(torch.cuda.is_available()),
        # best-model selection (may be ignored if unsupported by current TRL)
        "load_best_model_at_end": bool(args.load_best_model_at_end),
        "metric_for_best_model": str(args.metric_name),
        "greater_is_better": bool(args.greater_is_better),
    }
    import inspect

    if str(args.recipe).lower() == "dpo":
        # Assemble DPOConfig with version tolerance
        try:
            from trl import DPOConfig, DPOTrainer
        except Exception as e:
            raise SystemExit(f"TRL DPO components not available: {e}")

        # Inject DPO-specific keys if they exist in this version
        dpo_extra = {
            "beta": float(args.beta),
            "max_length": int(args.max_length),
            "max_prompt_length": int(args.max_prompt_length),
        }
        # Determine allowed fields for DPOConfig
        try:
            from dataclasses import fields as dc_fields
            from dataclasses import is_dataclass

            dpo_allowed = (
                set(f.name for f in dc_fields(DPOConfig))
                if is_dataclass(DPOConfig)
                else set()
            )
        except Exception:
            dpo_allowed = set()
        dpo_kwargs = base_kwargs | {
            k: v
            for k, v in dpo_extra.items()
            if (not dpo_allowed) or (k in dpo_allowed)
        }
        # Some TRL versions use eval_strategy instead of evaluation_strategy
        if (
            "evaluation_strategy" in dpo_kwargs
            and dpo_allowed
            and "evaluation_strategy" not in dpo_allowed
            and "eval_strategy" in dpo_allowed
        ):
            dpo_kwargs["eval_strategy"] = dpo_kwargs.pop("evaluation_strategy")
        training_args = DPOConfig(**dpo_kwargs)

        # Build kwargs for DPOTrainer
        trainer_kwargs = {
            "model": model,
            "train_dataset": train_ds,
            "eval_dataset": eval_ds,
        }
        try:
            params = set(inspect.signature(DPOTrainer.__init__).parameters.keys())
        except Exception:
            params = {"processing_class", "args"}
        # args vs config handling
        if "args" in params:
            trainer_kwargs["args"] = training_args
        elif "config" in params:
            trainer_kwargs["config"] = training_args
        # tokenizer arg name
        if "processing_class" in params:
            trainer_kwargs["processing_class"] = tokenizer
        elif "tokenizer" in params:
            trainer_kwargs["tokenizer"] = tokenizer
        # ref model handling across versions
        needs_ref = "ref_model" in params or "model_ref" in params
        if needs_ref:
            try:
                from trl import create_reference_model

                ref_model = create_reference_model(model)
            except Exception:
                ref_model = None
            if "ref_model" in params:
                trainer_kwargs["ref_model"] = ref_model
            if "model_ref" in params:
                trainer_kwargs["model_ref"] = ref_model

        trainer = DPOTrainer(**trainer_kwargs)
    else:
        # SFT path (default)
        try:
            from dataclasses import fields as dc_fields
            from dataclasses import is_dataclass

            allowed = (
                set(f.name for f in dc_fields(SFTConfig))
                if is_dataclass(SFTConfig)
                else set()
            )
        except Exception:
            allowed = set()
        if (
            "evaluation_strategy" in base_kwargs
            and allowed
            and "evaluation_strategy" not in allowed
            and "eval_strategy" in allowed
        ):
            base_kwargs["eval_strategy"] = base_kwargs.pop("evaluation_strategy")
        training_kwargs = {
            k: v for k, v in base_kwargs.items() if (not allowed) or (k in allowed)
        }
        training_args = SFTConfig(**training_kwargs)
        trainer_kwargs = {
            "model": model,
            "train_dataset": train_ds,
            "eval_dataset": eval_ds,
        }
        try:
            params = set(inspect.signature(SFTTrainer.__init__).parameters.keys())
        except Exception:
            params = {"tokenizer"}
        if "args" in params:
            trainer_kwargs["args"] = training_args
        elif "config" in params:
            trainer_kwargs["config"] = training_args
        if "processing_class" in params:
            trainer_kwargs["processing_class"] = tokenizer
        elif "tokenizer" in params:
            trainer_kwargs["tokenizer"] = tokenizer
        if "peft_config" in params and not hasattr(model, "peft_config"):
            trainer_kwargs["peft_config"] = lora_cfg
        trainer = SFTTrainer(**trainer_kwargs)

    print(f"[train_lora] Starting training ({args.recipe.upper()})…")
    trainer.train(
        resume_from_checkpoint=(
            str(args.resume_from_checkpoint) if args.resume_from_checkpoint else None
        )
    )
    print("[train_lora] Saving model…")
    trainer.save_model()
    print("[train_lora] Done.")


if __name__ == "__main__":
    main()
