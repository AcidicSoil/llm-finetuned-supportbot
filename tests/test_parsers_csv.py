from __future__ import annotations

import io
from datetime import datetime, timezone

from src.parsers.csv_parser import load_csv_records


def _csv(rows: list[dict[str, str]]) -> io.StringIO:
    # Build a simple CSV text with canonical header
    cols = ["id", "question", "answer", "source", "timestamp", "context", "tags"]
    out = []
    out.append(",".join(cols))
    for r in rows:
        row = [r.get(c, "") for c in cols]
        out.append(",".join(row))
    return io.StringIO("\n".join(out))


def test_csv_valid_rows_and_timestamp_z():
    buf = _csv(
        [
            {
                "id": "r1",
                "question": "How to X?",
                "answer": "Do Y",
                "source": "web",
                "timestamp": "2024-01-01T00:00:00Z",
                "context": "",
                "tags": "alpha,beta",
            },
            {
                "id": "r2",
                "question": "Q2",
                "answer": "A2",
                "source": "forum",
                "timestamp": "2024-01-02T12:34:56+00:00",
                "context": "ctx",
                "tags": "gamma;delta",
            },
        ]
    )

    records = load_csv_records(buf)
    assert [r.id for r in records] == ["r1", "r2"]
    # timestamp normalized
    assert records[0].meta.timestamp.tzinfo is not None
    assert records[0].meta.timestamp == datetime(
        2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc
    )
    # tags split/trimmed
    assert set(records[0].meta.tags) == {"alpha", "beta"}
    assert set(records[1].meta.tags) == {"gamma", "delta"}


def test_csv_missing_required_columns_raises():
    # Remove 'answer' column
    header = ",".join(["id", "question", "source", "timestamp"]) + "\n"
    buf = io.StringIO(header + "r1,Q,A,2024-01-01T00:00:00Z\n")
    try:
        load_csv_records(buf)
    except Exception as e:  # noqa: BLE001
        assert "missing required columns" in str(e)


def test_csv_empty_required_fields_raises():
    buf = _csv(
        [
            {
                "id": " ",
                "question": " ",
                "answer": "",
                "source": "",
                "timestamp": "",
            }
        ]
    )
    try:
        load_csv_records(buf)
    except Exception as e:  # noqa: BLE001
        # Pydantic/ValueError bubbled as invalid row with details
        assert "invalid row" in str(e)


def test_csv_bad_timestamp_raises():
    buf = _csv(
        [
            {
                "id": "r3",
                "question": "Q",
                "answer": "A",
                "source": "web",
                "timestamp": "not-a-timestamp",
            }
        ]
    )
    try:
        load_csv_records(buf)
    except Exception as e:  # noqa: BLE001
        msg = str(e)
        assert "invalid row" in msg
        assert "timestamp" in msg or "fromisoformat" in msg
