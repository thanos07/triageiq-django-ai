from __future__ import annotations

import re
from typing import Any

_INTERNAL = re.compile(r"<thinking>.*?</thinking>|<analysis>.*?</analysis>", re.IGNORECASE | re.DOTALL)
_DESTRUCTIVE = re.compile(
    r"\b(rm\s+-rf|drop\s+table|truncate\s+table|delete\s+from|kubectl\s+delete\s+(namespace|node)|disable\s+auth)\b",
    re.IGNORECASE,
)


def sanitize_text(value: str) -> str:
    return re.sub(r"\s{2,}", " ", _INTERNAL.sub("", value)).strip()


def sanitize_payload(value: Any) -> Any:
    if isinstance(value, str):
        return sanitize_text(value)
    if isinstance(value, list):
        return [sanitize_payload(item) for item in value]
    if isinstance(value, dict):
        cleaned = {str(key): sanitize_payload(item) for key, item in value.items()}
        if "confidence" in cleaned:
            try:
                cleaned["confidence"] = round(min(1.0, max(0.0, float(cleaned["confidence"]))), 4)
            except (TypeError, ValueError):
                cleaned["confidence"] = 0.0
        return cleaned
    return value


def destructive_action_flags(actions: list[str]) -> list[str]:
    return [action for action in actions if _DESTRUCTIVE.search(action)]
