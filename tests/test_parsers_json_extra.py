from __future__ import annotations

import io
import json
import pytest

from src.parsers.json_parser import load_json_records, load_jsonl_records


def test_json_top_level_wrong_type_raises():
    data = json.dumps({"not_records": []})
    with pytest.raises(Exception) as ei:
        load_json_records(io.StringIO(data))
    assert "expected a JSON array" in str(ei.value)


def test_json_records_key_with_invalid_item_raises():
    good = {
        "id": "ok",
        "inputs": {"question": "Q?", "context": None},
        "outputs": {"answer": "A"},
        "meta": {"source": "web", "timestamp": "2024-01-01T00:00:00Z", "tags": []},
    }
    bad = {
        "id": "bad",
        "inputs": {"question": "", "context": None},  # invalid empty question
        "outputs": {"answer": "A"},
        "meta": {"source": "web", "timestamp": "2024-01-01T00:00:00Z", "tags": []},
    }
    data = json.dumps({"records": [good, bad]})
    with pytest.raises(Exception) as ei:
        load_json_records(io.StringIO(data))
    assert "invalid record" in str(ei.value)


def test_jsonl_invalid_json_line_reports_line_no():
    lines = [
        '{"id": "r1", "inputs": {"question": "Q?", "context": null}, "outputs": {"answer": "A"}, "meta": {"source": "web", "timestamp": "2024-01-01T00:00:00Z", "tags": []}}',
        '{bad json line}',
    ]
    with pytest.raises(Exception) as ei:
        load_jsonl_records(io.StringIO("\n".join(lines)))
    msg = str(ei.value)
    assert "invalid JSON on line 2" in msg


def test_jsonl_invalid_record_reports_line_no():
    good = {
        "id": "ok",
        "inputs": {"question": "Q?", "context": None},
        "outputs": {"answer": "A"},
        "meta": {"source": "web", "timestamp": "2024-01-01T00:00:00Z", "tags": []},
    }
    bad = {
        "id": "bad",
        "inputs": {"question": " ", "context": None},  # invalid
        "outputs": {"answer": "A"},
        "meta": {"source": "web", "timestamp": "2024-01-01T00:00:00Z", "tags": []},
    }
    text = json.dumps(good) + "\n" + json.dumps(bad)
    with pytest.raises(Exception) as ei:
        load_jsonl_records(io.StringIO(text))
    assert "invalid record on line 2" in str(ei.value)

