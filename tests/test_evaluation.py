from __future__ import annotations

import types
import sys
import builtins


def make_fake_torch():
    m = types.SimpleNamespace()
    m.bfloat16 = object()  # just a sentinel
    return m


class _Recorder:
    def __init__(self, ret=None):
        self.calls = []
        self.ret = ret

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self.ret


def test_load_model_and_tokenizer_basic(monkeypatch):
    # Fake transformers module
    fake_transformers = types.SimpleNamespace()

    class _Tok:
        def __init__(self, name):
            self.name = name
            self.pad_token = None
            self.eos_token = "</s>"

        @classmethod
        def from_pretrained(cls, name):
            return cls(name)

    # Model recorder returns a dummy object
    model_obj = object()
    auto_model = _Recorder(ret=model_obj)
    fake_transformers.AutoTokenizer = _Tok
    fake_transformers.AutoModelForCausalLM = auto_model

    # Force stub modules to be used even if real ones were imported earlier
    sys.modules["transformers"] = fake_transformers
    sys.modules["torch"] = make_fake_torch()

    from src import evaluation as evalmod

    # Ensure quantization detection returns False to avoid requiring BitsAndBytes
    monkeypatch.setattr(evalmod, "_quantization_supported", lambda: False)

    model, tok = evalmod.load_model_and_tokenizer("base/model", quantization=False)

    # Tokenizer created and pad set from eos
    assert isinstance(tok, _Tok)
    assert tok.pad_token == tok.eos_token
    # AutoModel was called with device_map and maybe dtype
    assert auto_model.calls
    args, kwargs = auto_model.calls[-1]
    assert args == ("base/model",)
    assert kwargs.get("device_map") == "auto"


def test_load_model_and_tokenizer_quantization_path(monkeypatch):
    # Fake transformers with BitsAndBytesConfig
    class BitsAndBytesConfig:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class _Tok:
        def __init__(self, name):
            self.name = name
            self.pad_token = None
            self.eos_token = "</s>"

        @classmethod
        def from_pretrained(cls, name):
            return cls(name)

    model_obj = object()
    auto_model = _Recorder(ret=model_obj)

    fake_transformers = types.SimpleNamespace(
        AutoTokenizer=_Tok,
        AutoModelForCausalLM=auto_model,
        BitsAndBytesConfig=BitsAndBytesConfig,
    )
    sys.modules["transformers"] = fake_transformers
    sys.modules["torch"] = make_fake_torch()

    from src import evaluation as evalmod

    # Force quantization path
    monkeypatch.setattr(evalmod, "_quantization_supported", lambda: True)

    model, tok = evalmod.load_model_and_tokenizer("base/model", quantization=True)
    assert auto_model.calls
    _, kwargs = auto_model.calls[-1]
    qconf = kwargs.get("quantization_config")
    assert qconf is not None and getattr(qconf, "load_in_4bit", False)


def test_load_peft_model_merges(monkeypatch):
    # Fake peft module
    class _FakePeftModel:
        @classmethod
        def from_pretrained(cls, model, path):
            class _P:
                def merge_and_unload(self):
                    return "MERGED"

            return _P()

    fake_peft = types.SimpleNamespace(PeftModel=_FakePeftModel)
    sys.modules["peft"] = fake_peft

    from src import evaluation as evalmod

    merged = evalmod.load_peft_model(object(), "/tmp/adapter")
    assert merged == "MERGED"


def test_load_peft_model_missing():
    # Ensure peft import fails
    sys.modules.pop("peft", None)
    from src import evaluation as evalmod

    try:
        evalmod.load_peft_model(object(), "/tmp/x")
    except ImportError as e:
        assert "PEFT is not installed" in str(e)
