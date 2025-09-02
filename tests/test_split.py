from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from src.models import DataRecord, Inputs, Meta, Outputs
from src.split import split_records


def make_rec(idx: int, source: str, tags: list[str]) -> DataRecord:
    return DataRecord(
        id=f"r{idx}",
        inputs=Inputs(question=f"Q{idx}", context=None),
        outputs=Outputs(answer=f"A{idx}"),
        meta=Meta(
            source=source,
            timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
            tags=tags,
        ),
    )


def test_split_deterministic_and_unique():
    records: List[DataRecord] = []
    # 30 from source web, 20 from forum
    for i in range(30):
        records.append(make_rec(i, "web", ["auth"]))
    for j in range(30, 50):
        records.append(make_rec(j, "forum", ["account"]))

    r1 = split_records(
        records,
        train_ratio=0.7,
        val_ratio=0.2,
        test_ratio=0.1,
        seed=123,
        stratify_by="source",
    )
    r2 = split_records(
        records,
        train_ratio=0.7,
        val_ratio=0.2,
        test_ratio=0.1,
        seed=123,
        stratify_by="source",
    )

    ids1 = ({x.id for x in r1.train}, {x.id for x in r1.val}, {x.id for x in r1.test})
    ids2 = ({x.id for x in r2.train}, {x.id for x in r2.val}, {x.id for x in r2.test})
    assert ids1 == ids2
    assert not (ids1[0] & ids1[1] or ids1[0] & ids1[2] or ids1[1] & ids1[2])


def test_split_stratify_primary_tag_balances():
    # Two primary tags with different sizes; ensure both present in splits
    records: List[DataRecord] = []
    for i in range(40):
        records.append(make_rec(i, "web", ["alpha"]))
    for j in range(40, 60):
        records.append(make_rec(j, "web", ["beta"]))

    res = split_records(records, seed=7, stratify_by="primary_tag")

    # Check both tags appear across splits
    def tags(xs):
        return {t for r in xs for t in r.meta.tags}

    assert {"alpha", "beta"}.issubset(tags(res.train) | tags(res.val) | tags(res.test))


def test_split_ratio_totals():
    records = [make_rec(i, "s", ["t"]) for i in range(23)]
    res = split_records(
        records,
        train_ratio=0.6,
        val_ratio=0.2,
        test_ratio=0.2,
        seed=1,
        stratify_by="none",
    )
    assert len(res.train) + len(res.val) + len(res.test) == 23
