from __future__ import annotations

from typing import List, Sequence, Tuple


def sliding_windows(length: int, max_length: int, stride: int) -> List[Tuple[int, int]]:
    """Compute start/end indices (exclusive) for sliding windows.

    - Ensures at least one window when length <= max_length.
    - Uses step = max(max_length - stride, 1) to avoid zero/negative steps.
    - Always includes the final tail window so that the last token is covered.
    """
    if max_length <= 0:
        raise ValueError("max_length must be > 0")
    if stride < 0:
        raise ValueError("stride must be >= 0")

    if length <= max_length:
        return [(0, length)]

    step = max(max_length - stride, 1)
    windows: List[Tuple[int, int]] = []
    start = 0
    while start + max_length < length:
        windows.append((start, start + max_length))
        start += step
    # Tail window (align end to the sequence end)
    end_start = max(0, length - max_length)
    tail = (end_start, length)
    if not windows or windows[-1] != tail:
        windows.append(tail)
    return windows


def chunk_ids_sliding_window(
    ids: Sequence[int], *, max_length: int, stride: int, pad_id: int = 0
) -> Tuple[List[List[int]], List[List[int]]]:
    """Split token id sequence into overlapping, padded windows + attention masks.

    Returns (chunks, masks) where each chunk is length max_length and mask has 1 for
    real tokens and 0 for padding.
    """
    win_bounds = sliding_windows(len(ids), max_length=max_length, stride=stride)
    chunks: List[List[int]] = []
    masks: List[List[int]] = []
    for s, e in win_bounds:
        window = list(ids[s:e])
        pad = max(0, max_length - len(window))
        chunks.append(window + [pad_id] * pad)
        masks.append([1] * len(window) + [0] * pad)
    return chunks, masks


def last_window_for_text(
    tokenizer, text: str, *, max_length: int, stride: int
) -> Tuple[List[int], List[int]]:
    """Encode text without truncation and return the last sliding window.

    Useful for inference: keep the most recent context tokens up to max_length.
    """
    enc = tokenizer([text], padding=False, truncation=False, return_tensors=None)
    ids = list(enc["input_ids"][0])
    pad_id = getattr(tokenizer, "pad_token_id", 0) or 0
    chunks, masks = chunk_ids_sliding_window(
        ids, max_length=max_length, stride=stride, pad_id=pad_id
    )
    return chunks[-1], masks[-1]
