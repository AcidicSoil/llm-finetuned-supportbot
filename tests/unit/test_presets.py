r"""Unit tests for training presets and precedence.

These tests exercise the CLI argument parsing layer in `scripts/train_lora.py`.
They intentionally do not start a training loop; they only validate that:

- A selected preset from `configs/presets/` applies default values correctly.
- Precedence is enforced as: base defaults < preset < --config < CLI flags.
- Specific flags like `--fp16`, `--bf16`, and `--gradient-accumulation-steps`
  are set as expected for each preset.

Run just these tests:
  uv run pytest -q tests/unit/test_presets.py
Or on Windows if not using `uv`:
  .\.venv\Scripts\python -m pytest -q tests\unit\test_presets.py
"""

import sys

import yaml


def _run_parse(argv):
    # Import inside to ensure patched sys.argv is picked up by argparse
    import importlib

    sys.argv = ["pytest"] + argv
    mod = importlib.import_module("scripts.train_lora")
    return mod.parse_args()


def test_gpu_fp16_preset_sets_fp16(tmp_path):
    """`gpu-fp16` preset should enable fp16 and disable bf16."""
    args = _run_parse(
        [
            "--model",
            "dummy/model",
            "--splits-dir",
            str(tmp_path),
            "--output-dir",
            str(tmp_path / "out"),
            "--preset",
            "gpu-fp16",
        ]
    )
    assert args.fp16 is True
    assert args.bf16 is False


def test_cpu_preset_disables_amp(tmp_path):
    """`cpu` preset should leave AMP off and set GA to 1."""
    args = _run_parse(
        [
            "--model",
            "dummy/model",
            "--splits-dir",
            str(tmp_path),
            "--output-dir",
            str(tmp_path / "out"),
            "--preset",
            "cpu",
        ]
    )
    assert args.fp16 is False
    assert args.bf16 is False
    assert int(args.gradient_accumulation_steps) == 1


def test_memory_efficient_increases_accum(tmp_path):
    """`memory-efficient` preset should raise gradient accumulation to 8."""
    args = _run_parse(
        [
            "--model",
            "dummy/model",
            "--splits-dir",
            str(tmp_path),
            "--output-dir",
            str(tmp_path / "out"),
            "--preset",
            "memory-efficient",
        ]
    )
    assert int(args.gradient_accumulation_steps) == 8


def test_config_overrides_preset(tmp_path):
    """A YAML `--config` must override values introduced by a preset."""
    cfg = {"bf16": True, "fp16": False}
    cfg_path = tmp_path / "override.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg))

    args = _run_parse(
        [
            "--model",
            "dummy/model",
            "--splits-dir",
            str(tmp_path),
            "--output-dir",
            str(tmp_path / "out"),
            "--preset",
            "gpu-fp16",
            "--config",
            str(cfg_path),
        ]
    )
    # gpu-fp16 would set fp16=True; config should override to bf16
    assert args.bf16 is True
    assert args.fp16 is False


def test_cli_overrides_all(tmp_path):
    """Explicit CLI flags must override both preset and `--config` values."""
    args = _run_parse(
        [
            "--model",
            "dummy/model",
            "--splits-dir",
            str(tmp_path),
            "--output-dir",
            str(tmp_path / "out"),
            "--preset",
            "gpu-fp16",
            "--bf16",
        ]
    )
    assert args.bf16 is True
    assert args.fp16 is False
