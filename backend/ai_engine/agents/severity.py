from __future__ import annotations

from typing import Any

from ai_engine.agents.base import BaseAgent
from ai_engine.prompts import SEVERITY_SYSTEM
from ai_engine.schemas import SeverityResult


class SeverityAgent(BaseAgent[SeverityResult]):
    stage = "severity"
    schema = SeverityResult
    system_prompt = SEVERITY_SYSTEM

    def deterministic(self, context: dict[str, Any]) -> SeverityResult:
        incident = context.get("incident", context)
        text = " ".join(
            str(incident.get(key, ""))
            for key in ("title", "description", "business_impact", "environment")
        ).lower()

        critical_terms = ("all customers", "complete outage", "data loss", "breach", "security incident")
        high_terms = ("production", "payment", "checkout", "unavailable", "5xx", "latency", "failed")
        medium_terms = ("degraded", "intermittent", "staging", "slow")

        if any(term in text for term in critical_terms):
            level, confidence = "critical", 0.84
        elif sum(term in text for term in high_terms) >= 2:
            level, confidence = "high", 0.80
        elif any(term in text for term in medium_terms):
            level, confidence = "medium", 0.72
        else:
            level, confidence = "low", 0.64

        category = "availability"
        if "security" in text or "breach" in text:
            category = "security"
        elif "data" in text:
            category = "data-integrity"
        elif "payment" in text or "checkout" in text:
            category = "transaction-processing"

        signals = []
        if incident.get("environment") == "production":
            signals.append("Production environment is affected")
        if incident.get("business_impact"):
            signals.append("Business impact was explicitly reported")
        signals.append(f"Keyword and impact rules indicate {level} priority")

        return SeverityResult(
            level=level,
            urgency="Immediate response" if level in {"critical", "high"} else "Respond within normal on-call target",
            category=category,
            confidence=confidence,
            rationale=(
                f"The incident is classified as {level} based on the reported environment, "
                "scope, customer impact, and failure indicators. Human review remains required."
            ),
            signals=signals,
        )
