from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from src.models import DataRecord, Inputs, Outputs, Meta
from src.tokenization import tokenize_pairs


class FakeTokenizer:
    def __init__(self, vocab: Dict[str, int] | None = None):
        self.vocab = vocab or {}
        self.pad_id = 0

    def _encode(self, text: str, max_length: int, truncation: bool) -> List[int]:
        # naive whitespace tokenizer to integer ids
        toks = [self.vocab.setdefault(w, len(self.vocab) + 1) for w in text.split()]
        if truncation and len(toks) > max_length:
            toks = toks[: max_length]
        return toks

    def __call__(self, batch: List[str], padding=True, truncation=True, max_length=8, return_tensors=None):  # noqa: D401
        ids: List[List[int]] = [self._encode(x, max_length=max_length, truncation=bool(truncation)) for x in batch]
        if padding is True or padding == "max_length":
            for row in ids:
                row += [self.pad_id] * (max_length - len(row))
        attn: List[List[int]] = [[1 if t != self.pad_id else 0 for t in row] for row in ids]
        return {"input_ids": ids, "attention_mask": attn}


def make_record(i: int) -> DataRecord:
    return DataRecord(
        id=f"r{i}",
        inputs=Inputs(question=f"How are you {i}?", context=None),
        outputs=Outputs(answer=f"Fine {i}!"),
        meta=Meta(source="web", timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc), tags=["x"]),
    )


def test_tokenize_pairs_shapes_and_padding():
    records = [make_record(1), make_record(2)]
    tok = FakeTokenizer()
    out = tokenize_pairs(records, tok, max_length=6, padding="max_length", truncation=True)
    assert len(out.prompt_input_ids) == 2
    assert len(out.answer_input_ids) == 2
    # all rows padded to max_length
    assert all(len(row) == 6 for row in out.prompt_input_ids)
    assert all(len(row) == 6 for row in out.answer_input_ids)
    # attention mask aligns with padding (0s at tail)
    for row, mask in zip(out.prompt_input_ids, out.prompt_attention_mask):
        assert len(row) == len(mask)


def test_tokenize_pairs_truncation_applies():
    r = make_record(99)
    # create long question to exceed max_length 4
    r.inputs.question = "a b c d e f"
    tok = FakeTokenizer()
    out = tokenize_pairs([r], tok, max_length=4, padding="max_length", truncation=True)
    assert len(out.prompt_input_ids[0]) == 4

