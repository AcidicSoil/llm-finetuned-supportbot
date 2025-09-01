from __future__ import annotations

import importlib
import os
import pytest


def _libs_available() -> bool:
    for name in ("torch", "transformers"):
        try:
            importlib.import_module(name)
        except Exception:
            return False
    return True


@pytest.mark.smoke
@pytest.mark.skipif(not _libs_available(), reason="torch/transformers not available")
@pytest.mark.skipif(os.getenv("HF_HUB_OFFLINE") == "1", reason="HF Hub offline; tiny model unavailable")
def test_inference_generate_minimal():
    model_id = os.getenv("TEST_TINY_MODEL_ID", "sshleifer/tiny-gpt2")
    from src.evaluation import load_model_and_tokenizer

    model, tokenizer = load_model_and_tokenizer(model_id, quantization=False)
    inputs = tokenizer("Hello", return_tensors="pt").to(model.device)
    # Keep tiny generation
    with importlib.import_module("torch").no_grad():
        out = model.generate(**inputs, max_new_tokens=5)
    assert out is not None and out.shape[0] >= 1

