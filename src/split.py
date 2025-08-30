from __future__ import annotations

import hashlib
import math
import random
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Literal, Sequence, Tuple

from src.models import DataRecord


StratifyBy = Literal["none", "source", "primary_tag"]


def _stable_int(s: str) -> int:
    return int(hashlib.sha256(s.encode("utf-8")).hexdigest(), 16)


def _group_key(rec: DataRecord, mode: StratifyBy) -> str:
    if mode == "none":
        return "__all__"
    if mode == "source":
        return rec.meta.source
    if mode == "primary_tag":
        return rec.meta.tags[0] if rec.meta.tags else "__no_tag__"
    raise ValueError(f"unknown stratify mode: {mode}")


@dataclass
class SplitResult:
    train: List[DataRecord]
    val: List[DataRecord]
    test: List[DataRecord]


def split_records(
    records: Sequence[DataRecord],
    *,
    train_ratio: float = 0.8,
    val_ratio: float = 0.1,
    test_ratio: float = 0.1,
    seed: int = 42,
    stratify_by: StratifyBy = "source",
) -> SplitResult:
    """Deterministic stratified split of DataRecord sequence.

    - Ratios must sum to 1.0
    - Stratification by `source` (default), `primary_tag`, or "none".
    - Deterministic via fixed seed and stable sha256-derived per-group seeds.
    """
    n = len(records)
    if n == 0:
        return SplitResult([], [], [])
    total = train_ratio + val_ratio + test_ratio
    if not math.isclose(total, 1.0, rel_tol=0, abs_tol=1e-9):
        raise ValueError("train/val/test ratios must sum to 1.0")

    # Target global counts
    target_train = math.floor(n * train_ratio)
    target_val = math.floor(n * val_ratio)
    target_test = n - target_train - target_val

    # Group records by stratify key
    groups: Dict[str, List[DataRecord]] = {}
    for rec in records:
        key = _group_key(rec, stratify_by)
        groups.setdefault(key, []).append(rec)

    # Compute per-group base counts and fractional remainders for each split
    def per_split_counts(group_size: int, ratio: float) -> Tuple[int, float]:
        exact = group_size * ratio
        base = math.floor(exact)
        frac = exact - base
        return base, frac

    # Initialize allocations
    alloc_train: Dict[str, int] = {}
    alloc_val: Dict[str, int] = {}
    alloc_test: Dict[str, int] = {}

    base_train = base_val = base_test = 0
    fracs_train: List[Tuple[str, float]] = []
    fracs_val: List[Tuple[str, float]] = []
    fracs_test: List[Tuple[str, float]] = []

    for key, items in groups.items():
        m = len(items)
        b, f = per_split_counts(m, train_ratio)
        alloc_train[key] = b
        base_train += b
        fracs_train.append((key, f))

        b, f = per_split_counts(m, val_ratio)
        alloc_val[key] = b
        base_val += b
        fracs_val.append((key, f))

        # test remainder will be decided after train+val; use ratio-based too
        b, f = per_split_counts(m, test_ratio)
        alloc_test[key] = b
        base_test += b
        fracs_test.append((key, f))

    # Distribute remaining counts by largest fractional remainder with deterministic tie-break
    def distribute(
        target_total: int,
        base_total: int,
        alloc: Dict[str, int],
        fracs: List[Tuple[str, float]],
    ) -> None:
        remaining = target_total - base_total
        if remaining <= 0:
            return
        fracs_sorted = sorted(
            fracs,
            key=lambda kv: (kv[1], _stable_int(kv[0])),
            reverse=True,
        )
        for i in range(remaining):
            k = fracs_sorted[i % len(fracs_sorted)][0]
            alloc[k] += 1

    distribute(target_train, base_train, alloc_train, fracs_train)
    distribute(target_val, base_val, alloc_val, fracs_val)
    distribute(target_test, base_test, alloc_test, fracs_test)

    # Now, for each group, shuffle deterministically and slice
    train: List[DataRecord] = []
    val: List[DataRecord] = []
    test: List[DataRecord] = []

    for key, items in groups.items():
        local = list(items)
        rng = random.Random(seed ^ (_stable_int(key) & ((1 << 63) - 1)))
        rng.shuffle(local)
        t = alloc_train[key]
        v = alloc_val[key]
        w = alloc_test[key]
        # Adjust in case rounding overflowed group size due to numeric issues
        if t + v + w != len(local):
            # Recompute test as the remainder
            w = max(0, len(local) - t - v)
        train.extend(local[:t])
        val.extend(local[t : t + v])
        test.extend(local[t + v : t + v + w])

    # Sanity checks: no duplicates across splits
    def _ids(seq: Iterable[DataRecord]) -> set[str]:
        return {r.id for r in seq}

    ids_train, ids_val, ids_test = _ids(train), _ids(val), _ids(test)
    if ids_train & ids_val or ids_train & ids_test or ids_val & ids_test:
        raise AssertionError("duplicate ids detected across splits")

    return SplitResult(train=train, val=val, test=test)

