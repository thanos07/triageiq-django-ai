from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ai_engine.runbook_knowledge import retrieve_runbook_cases


class SearchRunbooksArgs(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    query: str = Field(min_length=1, max_length=300)


def search_runbooks(query: str) -> dict[str, Any]:
    cleaned = query.strip()
    context = {
        "incident": {
            "title": cleaned,
            "description": cleaned,
            "service_name": "",
            "business_impact": "",
            "extracted_context": {},
        },
        "severity": {},
        "root_cause": {},
    }
    matches = retrieve_runbook_cases(context, limit=3)
    return {
        "query": cleaned,
        "matches": [
            {
                "id": str(item.get("id", "")),
                "name": str(item.get("name", "")),
                "category": str(item.get("category", "")),
                "problem": str(item.get("problem", "")),
                "match_score": float(item.get("match_score", 0.0)),
            }
            for item in matches[:3]
        ],
    }
