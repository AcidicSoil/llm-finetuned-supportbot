from __future__ import annotations

from pathlib import Path
from typing import IO, Iterable, List, Sequence, Union, Any
import json

from pydantic import ValidationError

from src.models import DataRecord

PathLike = Union[str, Path]
FileLike = IO[str]


def _ensure_path(source: Union[PathLike, FileLike]) -> tuple[FileLike | None, FileLike]:
    if hasattr(source, "read"):
        return None, source  # type: ignore[return-value]
    f = open(Path(source), "r", encoding="utf-8")  # noqa: PTH123
    return f, f


def _to_records(seq: Iterable[dict[str, Any]]) -> List[DataRecord]:
    items: List[DataRecord] = []
    for idx, raw in enumerate(seq):
        try:
            # Prefer model_validate for dicts in Pydantic v2
            items.append(DataRecord.model_validate(raw))
        except ValidationError as e:
            raise ValueError(f"invalid record at index {idx}: {e}") from e
    return items


def load_json_records(source: Union[PathLike, FileLike]) -> List[DataRecord]:
    """Load a JSON array (or an object with key 'records') into DataRecord list.

    - Opens file paths with UTF-8 encoding
    - Expects either a JSON array of objects matching the schema, or an
      object containing a top-level key "records" that is such an array.
    """
    opened, fp = _ensure_path(source)
    try:
        obj = json.load(fp)
        if isinstance(obj, dict) and "records" in obj:
            val = obj["records"]
        else:
            val = obj
        if not isinstance(val, list):
            raise ValueError("expected a JSON array or object with key 'records'")
        return _to_records(val)
    finally:
        if opened is not None:
            opened.close()


def load_jsonl_records(source: Union[PathLike, FileLike]) -> List[DataRecord]:
    """Load newline-delimited JSON (JSONL/NDJSON) into DataRecord list.

    Each non-empty line must be a JSON object matching the schema.
    """
    opened, fp = _ensure_path(source)
    items: List[DataRecord] = []
    try:
        for line_no, line in enumerate(fp, start=1):
            s = line.strip()
            if not s:
                continue
            try:
                raw = json.loads(s)
            except json.JSONDecodeError as e:
                raise ValueError(f"invalid JSON on line {line_no}: {e}") from e
            try:
                items.append(DataRecord.model_validate(raw))
            except ValidationError as e:
                raise ValueError(f"invalid record on line {line_no}: {e}") from e
        return items
    finally:
        if opened is not None:
            opened.close()

