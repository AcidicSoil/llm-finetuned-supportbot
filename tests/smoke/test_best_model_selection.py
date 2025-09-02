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
def test_best_model_selection_sft_tiny():
    """Tiny SFT run with best-model selection flags should complete and save adapter."""
    model_id = os.getenv("TEST_TINY_MODEL_ID", "sshleifer/tiny-gpt2")

    def rec(i: int):
        return {
            "id": f"r{i}",
            "inputs": {"question": f"Hello {i}?", "context": None},
            "outputs": {"answer": f"Hi {i}!"},
            "meta": {
                "source": "smoke",
                "timestamp": "2024-01-01T00:00:00Z",
                "tags": ["smoke"],
            },
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

        write_jsonl(splits / "train.jsonl", [rec(i) for i in range(6)])
        write_jsonl(splits / "val.jsonl", [rec(i) for i in range(2)])

        from scripts import train_lora as T

        args = (
            T.parse_args.__wrapped__()
            if hasattr(T.parse_args, "__wrapped__")
            else T.parse_args()
        )
        args.model = model_id
        args.splits_dir = splits
        args.output_dir = out_dir
        args.epochs = 1
        args.per_device_train_batch_size = 1
        args.per_device_eval_batch_size = 1
        args.gradient_accumulation_steps = 1
        args.save_steps = 1
        args.eval_steps = 1
        args.load_best_model_at_end = True
        args.metric_name = "eval_loss"
        args.greater_is_better = False
        args.quant = "none"

        orig_parse = T.parse_args
        try:
            T.parse_args = lambda: args  # type: ignore[assignment]
            T.main()
        finally:
            T.parse_args = orig_parse

        assert (out_dir / "adapter_config.json").exists() or any(
            p.name == "adapter_config.json"
            for p in out_dir.rglob("adapter_config.json")
        )
