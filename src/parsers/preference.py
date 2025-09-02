from __future__ import annotations

import json
from pathlib import Path
from typing import IO, Iterable, List, Union, Any, Tuple

from datasets import Dataset

PathLike = Union[str, Path]
FileLike = IO[str]


def _ensure_path(source: Union[PathLike, FileLike]) -> Tuple[FileLike | None, FileLike]:
    if hasattr(source, "read"):
        return None, source  # type: ignore[return-value]
    f = open(Path(source), "r", encoding="utf-8")  # noqa: PTH123
    return f, f


def load_preference_jsonl(source: Union[PathLike, FileLike]) -> Dataset:
    """Load newline-delimited JSON containing preference pairs into a Dataset.

    Each non-empty line must be an object with keys: {"prompt", "chosen", "rejected"} (all strings).
    Returns a `datasets.Dataset` with columns ["prompt", "chosen", "rejected"].
    """
    opened, fp = _ensure_path(source)
    rows: List[dict[str, Any]] = []
    try:
        for line_no, line in enumerate(fp, start=1):
            s = line.strip()
            if not s:
                continue
            try:
                obj = json.loads(s)
            except json.JSONDecodeError as e:
                raise ValueError(f"invalid JSON on line {line_no}: {e}") from e
            for key in ("prompt", "chosen", "rejected"):
                if key not in obj or not isinstance(obj[key], str) or not obj[key].strip():
                    raise ValueError(
                        f"invalid record on line {line_no}: missing/non-string '{key}'"
                    )
            rows.append({
                "prompt": obj["prompt"].strip(),
                "chosen": obj["chosen"].strip(),
                "rejected": obj["rejected"].strip(),
            })
        if not rows:
            raise ValueError("no valid preference rows loaded")
        return Dataset.from_list(rows)
    finally:
        if opened is not None:
            opened.close()

