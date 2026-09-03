from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ai_engine.tools.demo_evidence import get_service_record, normalize_service_name

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_.-]+", re.IGNORECASE)


class SearchLogsArgs(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    service_name: str = Field(min_length=1, max_length=120)
    query: str = Field(min_length=1, max_length=240)


def _score(message: str, query: str) -> int:
    message = message.lower()
    tokens = {
        match.group(0).lower()
        for match in _TOKEN_RE.finditer(query)
        if len(match.group(0)) >= 3
    }
    return sum(3 for token in tokens if token in message) + (1 if "error" in message else 0)


def search_logs(service_name: str, query: str) -> dict[str, Any]:
    service = normalize_service_name(service_name)
    record = get_service_record(service)
    logs = list((record or {}).get("logs", []))
    ranked = sorted(logs, key=lambda item: -_score(str(item.get("message", "")), query))
    relevant = [item for item in ranked if _score(str(item.get("message", "")), query) > 0]
    return {
        "service_name": service,
        "query": query.strip(),
        "found": record is not None,
        "matches": (relevant or ranked)[:5],
    }
