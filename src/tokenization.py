from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, List, Sequence, Tuple, Union

from src.models import DataRecord

if TYPE_CHECKING:  # import for type checking only
    from transformers import PreTrainedTokenizerBase

TextPair = Tuple[str, str]


def default_pair_template(rec: DataRecord) -> TextPair:
    prompt = rec.inputs.question
    if rec.inputs.context:
        prompt += f"\n\n{rec.inputs.context}"
    answer = rec.outputs.answer
    return prompt, answer


@dataclass
class TokenizedPairs:
    prompt_input_ids: List[List[int]]
    prompt_attention_mask: List[List[int]]
    answer_input_ids: List[List[int]]
    answer_attention_mask: List[List[int]]


def _ensure_tokenizer(
    tokenizer_or_id: Union[str, "PreTrainedTokenizerBase"]
) -> "PreTrainedTokenizerBase":
    # Accept an already-initialized tokenizer-like object
    if hasattr(tokenizer_or_id, "__call__") and not isinstance(tokenizer_or_id, str):
        return tokenizer_or_id  # type: ignore[return-value]

    # Lazy import to avoid inserting real transformers into sys.modules during tests
    import importlib

    try:
        transformers = importlib.import_module("transformers")
    except Exception as e:  # pragma: no cover
        raise RuntimeError("transformers is required to load a tokenizer by id") from e

    AutoTokenizer = getattr(transformers, "AutoTokenizer")
    return AutoTokenizer.from_pretrained(str(tokenizer_or_id))


def tokenize_pairs(
    records: Sequence[DataRecord],
    tokenizer_or_id: Union[str, "PreTrainedTokenizerBase"],
    *,
    max_length: int = 512,
    padding: Union[bool, str] = "max_length",
    truncation: Union[bool, str] = True,
    pair_template=default_pair_template,
) -> TokenizedPairs:
    """Tokenize (prompt, answer) pairs from records.

    Returns TokenizedPairs with input_ids and attention_mask for prompt and answer
    separately, enabling downstream tasks (e.g., seq2seq or SFT) to compose labels.
    """
    tok = _ensure_tokenizer(tokenizer_or_id)
    prompts: List[str] = []
    answers: List[str] = []
    for rec in records:
        p, a = pair_template(rec)
        prompts.append(p)
        answers.append(a)

    enc_p = tok(
        prompts,
        padding=padding,
        truncation=truncation,
        max_length=max_length,
        return_tensors=None,
    )
    enc_a = tok(
        answers,
        padding=padding,
        truncation=truncation,
        max_length=max_length,
        return_tensors=None,
    )

    return TokenizedPairs(
        prompt_input_ids=list(enc_p["input_ids"]),
        prompt_attention_mask=list(enc_p["attention_mask"]),
        answer_input_ids=list(enc_a["input_ids"]),
        answer_attention_mask=list(enc_a["attention_mask"]),
    )
