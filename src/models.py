from __future__ import annotations

import re
from datetime import datetime
from typing import List, Optional, Sequence, Tuple, Union

from pydantic import BaseModel, field_validator


class Inputs(BaseModel):
    question: str
    context: Optional[str] = None

    @field_validator("question", mode="after")
    @classmethod
    def non_empty_question(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("question must be a non-empty string")
        return v.strip()


class Outputs(BaseModel):
    answer: str

    @field_validator("answer", mode="after")
    @classmethod
    def non_empty_answer(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("answer must be a non-empty string")
        return v.strip()


class Meta(BaseModel):
    source: str
    timestamp: datetime
    tags: List[str] = []

    @field_validator("source", mode="after")
    @classmethod
    def non_empty_source(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("source must be a non-empty string")
        return v.strip()

    @field_validator("tags", mode="after")
    @classmethod
    def validate_tags(cls, v: List[str]) -> List[str]:
        cleaned: List[str] = []
        for tag in v or []:
            if tag is None:
                raise ValueError("tags must not contain null entries")
            t = tag.strip()
            if not t:
                raise ValueError("tags must not contain empty strings")
            cleaned.append(t)
        return cleaned


class DataRecord(BaseModel):
    id: str
    inputs: Inputs
    outputs: Outputs
    meta: Meta
    schema_version: str = "1.0"

    @field_validator("id", mode="after")
    @classmethod
    def non_empty_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("id must be a non-empty string")
        return v.strip()


EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"\b(?:\+?\d[\s-]?)?(?:\(\d{2,3}\)[\s-]?)?\d{3}[\s-]?\d{4,}\b")


def validate_dataset(
    records: Sequence[DataRecord],
    *,
    allowed_tags: Optional[Sequence[str]] = None,
) -> Union[bool, Tuple[bool, List[str]]]:
    """Validate a collection of DataRecord items.

    Checks:
    - Duplicate `id` values
    - Simple PII scan on text fields (email/phone heuristics)
    - Tag vocabulary enforcement when `allowed_tags` provided

    Returns (ok, issues). If `ok` is False, at least one issue exists.
    """
    issues: List[str] = []

    # Duplicates
    seen = set()
    dups = set()
    for rec in records:
        if rec.id in seen:
            dups.add(rec.id)
        seen.add(rec.id)
    if dups:
        issues.append(f"duplicate ids detected: {sorted(dups)}")

    # Allowed tags
    if allowed_tags is not None:
        allowed = set(t.strip() for t in allowed_tags)
        for rec in records:
            disallowed = [t for t in rec.meta.tags if t not in allowed]
            if disallowed:
                issues.append(f"record {rec.id} has disallowed tags: {disallowed}")

    # Simple PII scan
    def scan_text(s: Optional[str]) -> bool:
        if not s:
            return False
        return bool(EMAIL_RE.search(s) or PHONE_RE.search(s))

    for rec in records:
        texts = [rec.inputs.question, rec.inputs.context or "", rec.outputs.answer]
        if any(scan_text(t) for t in texts):
            issues.append(
                f"record {rec.id} may contain PII (email/phone-like patterns)"
            )

    ok = len(issues) == 0
    # For convenience, return a bare bool in the common "all good" case
    # when no explicit tag policy is requested. Otherwise, return (ok, issues).
    if ok and allowed_tags is None:
        return True
    return ok, issues
