from __future__ import annotations

from typing import Any

from ai_engine.agents.base import BaseAgent
from ai_engine.prompts import ROOT_CAUSE_SYSTEM
from ai_engine.schemas import RootCauseResult


class RootCauseAgent(BaseAgent[RootCauseResult]):
    stage = "root_cause"
    schema = RootCauseResult
    system_prompt = ROOT_CAUSE_SYSTEM

    def deterministic(self, context: dict[str, Any]) -> RootCauseResult:
        incident = context.get("incident", {})
        investigation = context.get("investigation", {}) or {}
        investigation_text = " ".join([
            str(investigation.get("leading_hypothesis", "")),
            " ".join(str(item) for item in investigation.get("observations", []) or []),
            " ".join(str(item) for item in investigation.get("supporting_evidence", []) or []),
        ])
        text = (
            f"{incident.get('title', '')} {incident.get('description', '')} "
            f"{investigation_text}"
        ).lower()

        mappings = [
            (("deploy", "release", "rollback"), "Recent deployment regression", "deployment"),
            (("database", "db", "connection pool", "query"), "Database saturation or connectivity issue", "database"),
            (("timeout", "latency", "slow"), "Upstream dependency latency or resource saturation", "performance"),
            (("auth", "login", "token"), "Authentication or identity-provider failure", "authentication"),
            (("dns", "network", "gateway"), "Network path or gateway failure", "network"),
            (("payment", "checkout"), "Payment dependency or transaction-processing failure", "third-party-dependency"),
        ]
        probable, category = "Service resource saturation or an unobserved dependency failure", "unknown"
        evidence = []
        for terms, cause, mapped_category in mappings:
            matched = [term for term in terms if term in text]
            if matched:
                probable, category = cause, mapped_category
                evidence = [
                    (
                        f"Investigation evidence contains signal: {term}"
                        if term in investigation_text.lower()
                        else f"Incident text contains signal: {term}"
                    )
                    for term in matched[:3]
                ]
                break
        if not evidence:
            evidence = ["The reported symptoms indicate service-level failure but telemetry is incomplete"]

        source_gaps = [
            str(item.get("field", "")).replace("_", " ").strip()
            for item in incident.get("information_gaps", [])
            if isinstance(item, dict) and item.get("field")
        ]
        missing = list(dict.fromkeys(source_gaps + [
            "Recent deployment and configuration history",
            "Logs, traces, saturation metrics, and dependency health",
        ]))

        return RootCauseResult(
            probable_cause=probable,
            category=category,
            evidence=evidence,
            alternative_causes=[
                "Infrastructure capacity pressure",
                "Configuration drift or invalid secret",
                "Downstream dependency failure",
            ],
            missing_information=missing,
            confidence=0.68 if category != "unknown" else 0.52,
        )
