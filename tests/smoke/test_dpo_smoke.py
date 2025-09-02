from __future__ import annotations

import importlib
import json
import os
import tempfile
from pathlib import Path

import pytest


def _libs_available() -> bool:
    for name in ("torch", "transformers", "peft", "trl"):
        try:
            importlib.import_module(name)
        except Exception:
            return False
    return True


@pytest.mark.smoke
@pytest.mark.skipif(
    not _libs_available(), reason="torch/transformers/peft/trl not available"
)
@pytest.mark.skipif(
    os.getenv("HF_HUB_OFFLINE") == "1", reason="HF Hub offline; tiny model unavailable"
)
def test_dpo_training_one_step_tiny_model():
    """Run a tiny DPO step on a miniature preference dataset.

    Uses a very small community checkpoint. Skips when HF Hub is offline or libs missing.
    """
    model_id = os.getenv("TEST_TINY_MODEL_ID", "sshleifer/tiny-gpt2")

    def pref(i: int):
        return {
            "prompt": f"Hello {i}?",
            "chosen": f"Hi {i}!",
            "rejected": f"Goodbye {i}.",
        }

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        splits = tmp_path / "splits"
        splits.mkdir(parents=True, exist_ok=True)
        out_dir = tmp_path / "out"

        def write_jsonl(path: Path, items):
            with open(path, "w", encoding="utf-8") as f:
                for it in items:
                    f.write(json.dumps(it) + "\n")

        write_jsonl(splits / "train.dpo.jsonl", [pref(i) for i in range(4)])
        write_jsonl(splits / "val.dpo.jsonl", [pref(i) for i in range(2)])

        # Import training entry and invoke main with patched argv via argparse defaults
        from scripts import train_lora as T

        args = (
            T.parse_args.__wrapped__()
            if hasattr(T.parse_args, "__wrapped__")
            else T.parse_args()
        )
        args.model = model_id
        args.splits_dir = splits
        args.output_dir = out_dir
        args.recipe = "dpo"
        args.epochs = 1
        args.per_device_train_batch_size = 1
        args.per_device_eval_batch_size = 1
        args.gradient_accumulation_steps = 1
        args.save_steps = 1
        args.eval_steps = 1
        args.quant = "none"

        orig_parse = T.parse_args
        try:
            T.parse_args = lambda: args  # type: ignore[assignment]
            T.main()
        finally:
            T.parse_args = orig_parse

        # Adapter files should be saved (adapter_config.json exists under output)
        assert (out_dir / "adapter_config.json").exists() or any(
            p.name == "adapter_config.json"
            for p in out_dir.rglob("adapter_config.json")
        )
