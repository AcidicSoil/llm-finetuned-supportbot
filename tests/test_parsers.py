from __future__ import annotations

from datetime import datetime, timezone
import io
import json
import pytest

from src.models import DataRecord
from src.parsers import load_json_records, load_jsonl_records, load_csv_records


def _sample_record(idx: str = "r1"):
    return {
        "id": idx,
        "inputs": {"question": "Q?", "context": None},
        "outputs": {"answer": "A."},
        "meta": {
            "source": "web",
            "timestamp": datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc).isoformat(),
            "tags": ["auth", "account"],
        },
    }


def test_load_json_array_records():
    data = json.dumps([_sample_record("r1"), _sample_record("r2")])
    buf = io.StringIO(data)
    items = load_json_records(buf)
    assert [isinstance(x, DataRecord) for x in items]
    assert [x.id for x in items] == ["r1", "r2"]


def test_load_json_object_records_key():
    data = json.dumps({"records": [_sample_record("a"), _sample_record("b")]})
    items = load_json_records(io.StringIO(data))
    assert [x.id for x in items] == ["a", "b"]


def test_load_jsonl_records():
    lines = [json.dumps(_sample_record("x")), json.dumps(_sample_record("y"))]
    buf = io.StringIO("\n".join(lines))
    items = load_jsonl_records(buf)
    assert [x.id for x in items] == ["x", "y"]


def test_load_csv_records_comma_tags():
    csv_text = (
        "id,question,context,answer,source,timestamp,tags\n"
        "c1,How?,,Do!,web,2024-01-01T00:00:00Z,auth,account\n"
    )
    # Note: the above line has an extra comma; use quotes to be precise instead:
    csv_text = (
        "id,question,context,answer,source,timestamp,tags\n"
        'c1,How?,,Do!,web,2024-01-01T00:00:00Z,"auth,account"\n'
    )
    items = load_csv_records(io.StringIO(csv_text))
    assert len(items) == 1
    assert items[0].id == "c1"
    assert items[0].meta.tags == ["auth", "account"]


def test_load_csv_records_semicolon_tags():
    csv_text = (
        "id,question,context,answer,source,timestamp,tags\n"
        "c2,How?,,Do!,web,2024-01-01T00:00:00Z,auth;account\n"
    )
    items = load_csv_records(io.StringIO(csv_text))
    assert items[0].meta.tags == ["auth", "account"]


@pytest.mark.parametrize(
    "bad_json",
    [
        json.dumps([_sample_record("z") | {"inputs": {"question": ""}}]),
        json.dumps([_sample_record("z") | {"outputs": {"answer": "   "}}]),
    ],
)
def test_invalid_records_raise(bad_json):
    with pytest.raises(Exception):
        load_json_records(io.StringIO(bad_json))

