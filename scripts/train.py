#!/usr/bin/env python3
"""Thin alias for scripts/train_lora.py to match docs/PRD examples.

Usage:
  uv run scripts/train.py --config configs/sft.yaml [overrides...]
"""

try:
    # Prefer importing and calling main for clearer tracebacks
    from scripts.train_lora import main as _main  # type: ignore
except Exception:  # pragma: no cover - fallback when import path differs
    import os
    import runpy

    HERE = os.path.dirname(__file__)
    runpy.run_path(os.path.join(HERE, "train_lora.py"), run_name="__main__")
else:
    if __name__ == "__main__":
        _main()
