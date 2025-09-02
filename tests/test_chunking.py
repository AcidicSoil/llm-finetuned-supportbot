from __future__ import annotations

from src.chunking import chunk_ids_sliding_window, sliding_windows


def test_sliding_windows_basic():
    # length <= max -> single window
    assert sliding_windows(5, max_length=8, stride=2) == [(0, 5)]
    # overlapping windows + tail
    wins = sliding_windows(30, max_length=10, stride=2)
    # step = 8, expect windows at 0..10, 8..18, 16..26, tail 20..30
    assert wins[0] == (0, 10)
    assert wins[1] == (8, 18)
    assert wins[2] == (16, 26)
    assert wins[-1] == (20, 30)


def test_chunk_ids_masks_lengths_and_overlap():
    ids = list(range(25))
    chunks, masks = chunk_ids_sliding_window(ids, max_length=8, stride=2, pad_id=0)
    # Expected windows start at 0,6,12,17 (tail 17..25)
    assert len(chunks) == len(masks) >= 3
    # All chunks padded to max_length
    assert all(len(c) == 8 for c in chunks)
    # Masks align: 1s for tokens, 0s for padding
    for c, m in zip(chunks, masks):
        assert len(c) == len(m)
        # padding only at tail
        if 0 in m:
            pad_start = m.index(0)
            assert all(x == 0 for x in m[pad_start:])


def test_chunk_ids_short_sequence_single_window():
    ids = [1, 2, 3]
    chunks, masks = chunk_ids_sliding_window(ids, max_length=8, stride=2, pad_id=0)
    assert len(chunks) == 1
    assert chunks[0][:3] == ids
    assert masks[0][:3] == [1, 1, 1]
    assert all(x == 0 for x in chunks[0][3:])
