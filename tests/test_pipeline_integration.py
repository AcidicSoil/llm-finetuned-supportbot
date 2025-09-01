from __future__ import annotations

from datetime import datetime, timezone

from src.models import DataRecord, Inputs, Outputs, Meta, validate_dataset
from src.tokenization import tokenize_pairs
from src.split import split_records


class _FakeTok:
    def __init__(self):
        self.pad_id = 0
        self.vocab = {}

    def _enc(self, s: str, max_length: int, truncation: bool):
        toks = [self.vocab.setdefault(w, len(self.vocab) + 1) for w in s.split()]
        if truncation and len(toks) > max_length:
            toks = toks[: max_length]
        return toks

    def __call__(self, batch, padding=True, truncation=True, max_length=8, return_tensors=None):
        ids = [self._enc(x, max_length, bool(truncation)) for x in batch]
        if padding is True or padding == "max_length":
            for row in ids:
                row += [self.pad_id] * (max_length - len(row))
        attn = [[1 if t != self.pad_id else 0 for t in row] for row in ids]
        return {"input_ids": ids, "attention_mask": attn}


def _rec(i: int, src: str, tag: str) -> DataRecord:
    return DataRecord(
        id=f"r{i}",
        inputs=Inputs(question=f"How are you {i}?", context=None),
        outputs=Outputs(answer=f"Fine {i}!"),
        meta=Meta(source=src, timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc), tags=[tag]),
    )


def test_end_to_end_small_pipeline():
    # Build small dataset
    data = [_rec(i, "web" if i % 2 == 0 else "forum", "alpha" if i % 3 == 0 else "beta") for i in range(10)]

    # Validate dataset
    ok = validate_dataset(data)
    assert ok is True

    # Tokenize pairs
    out = tokenize_pairs(data, _FakeTok(), max_length=6, padding="max_length", truncation=True)
    assert len(out.prompt_input_ids) == 10
    assert all(len(r) == 6 for r in out.prompt_input_ids)

    # Split
    split = split_records(data, seed=7, stratify_by="source")
    total = len(split.train) + len(split.val) + len(split.test)
    assert total == 10
