from __future__ import annotations

from enum import Enum
from typing import Optional


class ErrorType(str, Enum):
    REFUSAL = "refusal"
    HALLUCINATION = "hallucination"
    STYLE = "style"
    OTHER = "other"


def classify_error(prompt: str, response: str) -> Optional[ErrorType]:
    """Heuristic error classifier.

    - REFUSAL: detects generic refusals (e.g., "I can't"/"cannot help").
    - STYLE: overly terse single-word responses.
    - HALLUCINATION: placeholder; requires ground truth to detect reliably. Returns None here.
    - OTHER: fallback for mismatches not captured above.

    Returns None when no obvious error is detected.
    """
    text = (response or "").lower().strip()
    if not text:
        return ErrorType.OTHER
    if any(p in text for p in ["i can't", "cannot", "not able to", "sorry, i can't"]):
        return ErrorType.REFUSAL
    if len(text.split()) <= 2:
        return ErrorType.STYLE
    # Hallucination detection would need references; skip here
    return None

