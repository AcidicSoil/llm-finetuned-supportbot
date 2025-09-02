from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import IO, List, Optional, Union

from pydantic import ValidationError

from src.models import DataRecord, Inputs, Meta, Outputs

PathLike = Union[str, Path]
FileLike = IO[str]


def _ensure_path(source: Union[PathLike, FileLike]) -> tuple[FileLike | None, FileLike]:
    # csv docs recommend newline="" when opening files
    if hasattr(source, "read"):
        return None, source  # type: ignore[return-value]
    f = open(Path(source), "r", encoding="utf-8", newline="")  # noqa: PTH123
    return f, f


def _parse_timestamp(value: str) -> datetime:
    # Accept ISO 8601, including Z suffix; normalize Z -> +00:00
    s = (value or "").strip()
    if not s:
        raise ValueError("timestamp is required")
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)


def _parse_tags(value: Optional[str]) -> list[str]:
    if not value:
        return []
    # Allow comma or semicolon separators
    raw = [t.strip() for part in value.split(";") for t in part.split(",")]
    return [t for t in raw if t]


def load_csv_records(source: Union[PathLike, FileLike]) -> List[DataRecord]:
    """Load DataRecord list from a CSV with a canonical header.

    Required columns:
      - id, question, answer, source, timestamp
    Optional columns:
      - context, tags (comma/semicolon-separated)
    """
    opened, fp = _ensure_path(source)
    try:
        # Use restkey so trailing, unquoted commas in last column (e.g., tags)
        # don't get silently dropped by the csv module; we'll merge them below.
        reader = csv.DictReader(fp, restkey="__rest__")
        required = {"id", "question", "answer", "source", "timestamp"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"missing required columns: {sorted(missing)}")

        items: List[DataRecord] = []
        for row_idx, row in enumerate(reader, start=2):  # include header line
            try:
                # Merge any overflow columns (from restkey) into the tags field
                raw_tags = row.get("tags") or ""
                overflow = row.get("__rest__")
                if overflow:
                    # join extras with commas to be parsed by _parse_tags
                    raw_tags = ",".join(
                        [raw_tags] + [str(x) for x in overflow if x is not None]
                    ).strip(", ")

                rec = DataRecord(
                    id=(row.get("id") or "").strip(),
                    inputs=Inputs(
                        question=(row.get("question") or "").strip(),
                        context=(row.get("context") or None),
                    ),
                    outputs=Outputs(
                        answer=(row.get("answer") or "").strip(),
                    ),
                    meta=Meta(
                        source=(row.get("source") or "").strip(),
                        timestamp=_parse_timestamp(row.get("timestamp") or ""),
                        tags=_parse_tags(raw_tags),
                    ),
                )
            except (ValidationError, Exception) as e:  # noqa: BLE001
                raise ValueError(f"invalid row {row_idx}: {e}") from e
            items.append(rec)
        return items
    finally:
        if opened is not None:
            opened.close()
