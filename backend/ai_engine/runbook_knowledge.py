from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_DATA_PATH = Path(__file__).resolve().parent / "data" / "runbook_cases.json"


@lru_cache(maxsize=1)
def load_runbook_cases() -> tuple[dict[str, Any], ...]:
    """Load and cache the versioned runbook knowledge base."""
    with _DATA_PATH.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, list):
        raise ValueError("runbook_cases.json must contain a JSON array")
    return tuple(item for item in payload if isinstance(item, dict))


def build_search_text(context: dict[str, Any]) -> str:
    """Primary text: direct incident evidence receives the strongest retrieval weight."""
    incident = context.get("incident", {}) or {}
    parts = [
        incident.get("title", ""),
        incident.get("description", ""),
        incident.get("service_name", ""),
        incident.get("business_impact", ""),
        " ".join(str(value) for value in (incident.get("extracted_context", {}) or {}).values()),
    ]
    return " ".join(str(part) for part in parts if part).lower()


def build_supplemental_text(context: dict[str, Any]) -> str:
    """Secondary AI-derived context helps tie-break but cannot overpower source evidence."""
    severity = context.get("severity", {}) or {}
    root_cause = context.get("root_cause", {}) or {}
    parts = [
        severity.get("category", ""),
        root_cause.get("category", ""),
        root_cause.get("probable_cause", ""),
        " ".join(str(item) for item in root_cause.get("evidence", []) or []),
    ]
    return " ".join(str(part) for part in parts if part).lower()


def score_runbook_case(
    case: dict[str, Any],
    search_text: str,
    supplemental_text: str = "",
) -> float:
    """Transparent source-first keyword/category retrieval for the runbook RAG demo."""
    primary = search_text.lower()
    supplemental = supplemental_text.lower()
    score = 0.0

    category = str(case.get("category", "")).lower().strip()
    if category and category not in {"unknown", "general"}:
        if category in primary:
            score += 4.0
        elif category in supplemental:
            score += 1.0

    for keyword in case.get("keywords", []) or []:
        keyword_text = str(keyword).lower().strip()
        if not keyword_text:
            continue
        phrase = " " in keyword_text
        if keyword_text in primary:
            score += 5.0 if phrase else 2.0
        elif keyword_text in supplemental:
            score += 1.5 if phrase else 0.5

    name_tokens = {
        token.strip("/()-").lower()
        for token in str(case.get("name", "")).split()
        if len(token.strip("/()-")) >= 5
    }
    score += min(3.0, sum(0.5 for token in name_tokens if token in primary))
    return round(score, 2)


def retrieve_runbook_cases(
    context: dict[str, Any],
    *,
    limit: int = 3,
) -> list[dict[str, Any]]:
    search_text = build_search_text(context)
    supplemental_text = build_supplemental_text(context)
    ranked: list[dict[str, Any]] = []
    for case in load_runbook_cases():
        ranked.append({
            **case,
            "match_score": score_runbook_case(case, search_text, supplemental_text),
        })
    ranked.sort(key=lambda item: (-float(item["match_score"]), str(item.get("id", ""))))

    if not ranked or float(ranked[0]["match_score"]) <= 0:
        fallback = next((item for item in ranked if item.get("id") == "rb-030"), None)
        return [fallback] if fallback else []
    return ranked[: max(1, limit)]


def get_runbook_case(case_id: str) -> dict[str, Any] | None:
    return next((case for case in load_runbook_cases() if case.get("id") == case_id), None)
