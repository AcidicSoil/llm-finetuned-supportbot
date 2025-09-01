"""Lightweight evaluation helpers for demo/inference.

Functions avoid heavy imports at module import time and only import
dependencies inside call-sites, so tests can stub/mocks libs easily.
"""

from __future__ import annotations

from typing import Tuple


def _quantization_supported() -> bool:
    """Best-effort check for 4-bit quantization support.

    Returns True if both transformers' BitsAndBytesConfig and the bitsandbytes
    runtime are importable; otherwise False. This avoids surfacing cryptic
    runtime errors when users pass --quantization without the backend installed.
    """
    try:
        # transformers exposes BitsAndBytesConfig at top-level in recent versions
        import importlib

        importlib.import_module("bitsandbytes")
        importlib.import_module("transformers")
        # If transformers is present, BitsAndBytesConfig is typically available; if not,
        # we'll still return True and let model loading raise a clearer error.
        return True
    except Exception:
        return False


def load_model_and_tokenizer(base_model_name: str, quantization: bool = False):
    """Load a causal LM model and tokenizer for inference.

    - Uses device_map='auto' and bfloat16 when available.
    - If `quantization` is True and the environment supports it, configures
      4-bit NF4 quantization with bfloat16 compute.

    Returns a tuple (model, tokenizer).
    """
    try:
        import importlib

        torch = importlib.import_module("torch")
        transformers = importlib.import_module("transformers")
    except Exception as e:
        raise ImportError(
            "Transformers and torch are required to load models for inference."
        ) from e

    AutoTokenizer = getattr(transformers, "AutoTokenizer")
    AutoModelForCausalLM = getattr(transformers, "AutoModelForCausalLM")

    tokenizer = AutoTokenizer.from_pretrained(base_model_name)

    dtype = getattr(torch, "bfloat16", None)
    # Build kwargs for model loading
    model_kwargs = {
        "device_map": "auto",
    }
    if dtype is not None:
        model_kwargs["torch_dtype"] = dtype

    if quantization and _quantization_supported():
        # Try to build a BitsAndBytesConfig for 4-bit NF4
        BitsAndBytesConfig = getattr(transformers, "BitsAndBytesConfig", None)
        if BitsAndBytesConfig is not None:
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=dtype,
            )
            model_kwargs["quantization_config"] = bnb_config

    # Load model weights from pretrained checkpoint
    model = AutoModelForCausalLM.from_pretrained(base_model_name, **model_kwargs)

    # Ensure pad token exists to allow batching/generation convenience
    if getattr(tokenizer, "pad_token", None) is None and getattr(tokenizer, "eos_token", None) is not None:
        tokenizer.pad_token = tokenizer.eos_token

    return model, tokenizer


def load_peft_model(model, peft_model_path: str):
    """Utility to load a PEFT adapter and merge it into a base model.

    This will require the optional `peft` package. On success, returns a model
    with LoRA (or other) weights merged via `merge_and_unload()`.
    """
    try:
        import importlib

        peft = importlib.import_module("peft")
    except Exception as e:
        raise ImportError(
            "PEFT is not installed. Please `pip install peft` to use adapters."
        ) from e

    PeftModel = getattr(peft, "PeftModel")
    peft_model = PeftModel.from_pretrained(model, peft_model_path)
    merged = peft_model.merge_and_unload()
    return merged
