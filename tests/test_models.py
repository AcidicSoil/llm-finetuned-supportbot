from __future__ import annotations

from datetime import datetime
import pytest

from src.models import DataRecord, Inputs, Meta, Outputs, validate_dataset


def make_record(**overrides):
    base = dict(
        id="rec-1",
        inputs=dict(question="How to reset my password?", context=None),
        outputs=dict(answer="Use the reset link sent to your email."),
        meta=dict(source="support_forum", timestamp=datetime.utcnow(), tags=["auth", "account"]),
    )
    base.update(overrides)
    return DataRecord(**base)


def test_model_happy_path():
    rec = make_record()
    assert rec.id == "rec-1"
    assert rec.schema_version == "1.0"
    assert rec.inputs.question
    assert rec.outputs.answer
    assert rec.meta.source
    assert rec.meta.tags == ["auth", "account"]


@pytest.mark.parametrize(
    "field, update",
    [
        ("id", dict(id="   ")),
        ("question", dict(inputs=dict(question=""))),
        ("answer", dict(outputs=dict(answer="   "))),
        ("source", dict(meta=dict(source=""))),
        ("tags", dict(meta=dict(tags=["ok", " "]))),
    ],
)
def test_string_fields_cannot_be_empty(field, update):
    with pytest.raises(Exception):
        make_record(**update)


def test_validate_dataset_duplicate_ids_and_disallowed_tags():
    r1 = make_record(id="a", meta=dict(source="web", timestamp=datetime.utcnow(), tags=["ok"]))
    r2 = make_record(id="a", meta=dict(source="web", timestamp=datetime.utcnow(), tags=["bad"]))
    ok, issues = validate_dataset([r1, r2], allowed_tags=["ok", "auth", "account"])
    assert not ok
    assert any("duplicate ids" in msg for msg in issues)
    assert any("disallowed tags" in msg for msg in issues)


def test_validate_dataset_pii_scan_detects_email_like_patterns():
    r = make_record(
        id="pii",
        inputs=dict(question="Contact me at email@example.com", context=None),
    )
    ok, issues = validate_dataset([r])
    assert not ok
    assert any("may contain PII" in msg for msg in issues)

