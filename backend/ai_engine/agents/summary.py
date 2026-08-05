from __future__ import annotations

from typing import Any

from ai_engine.agents.base import BaseAgent
from ai_engine.prompts import SUMMARY_SYSTEM
from ai_engine.schemas import SummaryResult


class SummaryAgent(BaseAgent[SummaryResult]):
    stage = "summary"
    schema = SummaryResult
    system_prompt = SUMMARY_SYSTEM

    def deterministic(self, context: dict[str, Any]) -> SummaryResult:
        incident = context.get("incident", {})
        severity = context.get("severity", {})
        root = context.get("root_cause", {})
        service = incident.get("service_name", "the affected service")
        level = severity.get("level", "unknown")
        cause = root.get("probable_cause", "an unconfirmed operational cause")
        impact = incident.get("business_impact") or "User impact is being assessed."

        return SummaryResult(
            technical_summary=(
                f"{service} is experiencing a {level}-severity incident. The leading hypothesis is "
                f"{cause.lower()}. Responders should validate telemetry before applying the recommended mitigation."
            ),
            executive_summary=(
                f"An incident is affecting {service}. The response team has completed initial AI-assisted triage, "
                "and a human reviewer must approve the remediation plan before closure."
            ),
            customer_update=(
                "We are investigating a service issue that may affect some requests. Our team is working on mitigation "
                "and will provide another update after recovery checks are complete."
            ),
            business_impact=impact,
            next_update="Provide the next update after a mitigation is applied or within 30 minutes, whichever comes first.",
            confidence=0.76,
        )
