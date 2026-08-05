from __future__ import annotations

from typing import Any

from ai_engine.agents.base import BaseAgent
from ai_engine.prompts import RUNBOOK_SYSTEM
from ai_engine.guardrails import destructive_action_flags
from ai_engine.runbook_knowledge import retrieve_runbook_cases
from ai_engine.schemas import MissingInformation, RunbookResult, RunbookStep


COLLECTION_GUIDANCE = {
    "environment": ("Confirm the runtime environment from deployment metadata or the service owner.", None),
    "business_impact": ("Review user-impact dashboards, failed transactions, support tickets, and affected regions.", None),
    "reported_severity": ("Ask the incident commander for the initial priority and compare it with impact evidence.", None),
    "incident_start_time": ("Find the earliest matching alert, log event, deployment event, or user report.", None),
    "deployment_version": ("Review the deployment history for the affected service.", "kubectl rollout history deployment/<service>"),
    "diagnostic_evidence": ("Collect ERROR/FATAL logs, traces, saturation metrics, and dependency health around the incident window.", None),
    "logs_traces_saturation_metrics_and_dependency_health": ("Collect ERROR/FATAL logs, recent traces, CPU/memory saturation, queue depth, and downstream health.", None),
    "recent_deployment_and_configuration_history": ("Review deployment, feature-flag, secret, and configuration changes immediately before the incident.", None),
}


class RunbookAgent(BaseAgent[RunbookResult]):
    stage = "runbook"
    schema = RunbookResult
    system_prompt = RUNBOOK_SYSTEM

    def build_prompt(self, context: dict[str, Any]) -> str:
        enriched = dict(context)
        enriched["retrieved_runbook_cases"] = retrieve_runbook_cases(context, limit=3)
        return super().build_prompt(enriched)

    def postprocess(self, output: RunbookResult) -> RunbookResult:
        flags = destructive_action_flags([step.action for step in output.steps])
        if flags:
            output.escalate = True
            output.escalation_reason = (
                (output.escalation_reason + " ") if output.escalation_reason else ""
            ) + "Potentially destructive action detected; explicit human approval is required."
            for step in output.steps:
                if step.action in flags and not step.action.upper().startswith("CAUTION:"):
                    step.action = "CAUTION: " + step.action
                    step.risk = "high"
        if output.confidence < 0.55:
            output.escalate = True
            output.escalation_reason = (
                (output.escalation_reason + " ") if output.escalation_reason else ""
            ) + "Low-confidence response plan requires escalation."
        return output

    def _missing_items(self, context: dict[str, Any]) -> list[MissingInformation]:
        incident = context.get("incident", {})
        root_cause = context.get("root_cause", {})
        items: list[MissingInformation] = []
        seen: set[str] = set()

        for raw in incident.get("information_gaps", []) or []:
            if not isinstance(raw, dict):
                continue
            field = str(raw.get("field", "unknown_information")).strip() or "unknown_information"
            if field in seen:
                continue
            seen.add(field)
            items.append(MissingInformation(
                field=field,
                reason_required=str(raw.get("reason_required", "This information is needed to validate the response plan.")),
                collection_method=str(raw.get("collection_method", "Ask the service owner or collect the relevant telemetry.")),
                example_command=raw.get("example_command") or None,
                blocks_resolution=bool(raw.get("blocks_resolution", False)),
                fallback_action=raw.get("fallback_action") or "Continue only with reversible diagnostics and document the uncertainty.",
            ))

        for text in root_cause.get("missing_information", []) or []:
            label = str(text).strip()
            if not label:
                continue
            field = label.lower().replace("/", " ").replace("-", " ")
            field = "_".join(field.split())[:80]
            if field in seen:
                continue
            seen.add(field)
            collection, command = COLLECTION_GUIDANCE.get(
                field,
                (f"Collect or confirm: {label}.", None),
            )
            items.append(MissingInformation(
                field=field,
                reason_required=f"{label} is needed to validate the leading root-cause hypothesis.",
                collection_method=collection,
                example_command=command,
                blocks_resolution=False,
                fallback_action="Avoid irreversible changes until supporting evidence is available.",
            ))
        return items

    @staticmethod
    def _step(order: int, action: str, rationale: str, verification: str, risk: str = "low") -> RunbookStep:
        return RunbookStep(
            order=order,
            action=action,
            rationale=rationale,
            verification=verification,
            risk=risk,
        )

    def deterministic(self, context: dict[str, Any]) -> RunbookResult:
        severity = context.get("severity", {})
        missing_information = self._missing_items(context)
        matches = retrieve_runbook_cases(context, limit=3)
        case = matches[0] if matches else {
            "id": "rb-030",
            "name": "Unknown or insufficiently observed incident",
            "problem": "The incident lacks enough evidence for a specific remediation.",
            "match_score": 0.0,
            "diagnostic_steps": [],
            "solution_steps": [],
            "verification_steps": [],
            "rollback_plan": ["Stop any mitigation that worsens impact and restore the last known-good state."],
            "escalation_triggers": [],
            "caution": "Avoid irreversible actions without supporting evidence.",
            "missing_information": [],
        }

        steps: list[RunbookStep] = [
            self._step(
                1,
                "Confirm the current blast radius, incident commander, and communication channel.",
                "A coordinated response prevents conflicting changes and establishes accountability.",
                "Affected services, regions, users, owner, and update cadence are recorded.",
            )
        ]
        order = 2
        if missing_information:
            steps.append(self._step(
                order,
                "Collect or explicitly waive the missing information listed in this runbook before irreversible changes.",
                "The source and telemetry do not contain every fact required to validate the diagnosis.",
                "Each gap is filled, marked unavailable, or waived by an accountable human with a fallback action.",
            ))
            order += 1

        for diagnostic in case.get("diagnostic_steps", []) or []:
            steps.append(self._step(
                order,
                str(diagnostic),
                f"This diagnostic is part of the matched knowledge case {case.get('id')}: {case.get('name')}.",
                "The result is timestamped and attached to the incident evidence.",
                "low",
            ))
            order += 1

        for solution in case.get("solution_steps", []) or []:
            steps.append(self._step(
                order,
                str(solution),
                "This is a bounded mitigation from the matched problem–solution case.",
                "The targeted failure signal improves without a new safety, data, or customer-impact regression.",
                "medium",
            ))
            order += 1

        for verification in case.get("verification_steps", []) or []:
            steps.append(self._step(
                order,
                f"Verify: {verification}",
                "Resolution requires both technical and user-visible recovery evidence.",
                str(verification),
                "low",
            ))
            order += 1

        high_severity = severity.get("level") in {"critical", "high"}
        blockers = any(item.blocks_resolution for item in missing_information)
        escalation_triggers = [str(item) for item in case.get("escalation_triggers", []) or []]
        caution = str(case.get("caution", "")).strip()
        escalation_reason_parts = []
        if high_severity:
            escalation_reason_parts.append("High-impact incident requires service-owner and incident-commander visibility.")
        if blockers:
            escalation_reason_parts.append("One or more information gaps block confident resolution.")
        if escalation_triggers:
            escalation_reason_parts.append("Escalate if: " + "; ".join(escalation_triggers) + ".")
        if caution:
            escalation_reason_parts.append("Safety caution: " + caution)

        return RunbookResult(
            title=f"{case.get('name')} response plan",
            matched_case_id=str(case.get("id", "")),
            matched_case_name=str(case.get("name", "")),
            problem_summary=str(case.get("problem", "")),
            match_score=float(case.get("match_score", 0.0)),
            related_cases=[
                f"{item.get('id')}: {item.get('name')}"
                for item in matches[1:]
            ],
            required_evidence=[str(item) for item in case.get("missing_information", []) or []],
            steps=steps,
            missing_information=missing_information,
            escalate=high_severity or blockers,
            escalation_reason=" ".join(escalation_reason_parts),
            rollback_plan=[str(item) for item in case.get("rollback_plan", []) or []],
            confidence=min(0.92, 0.62 + min(float(case.get("match_score", 0.0)), 30.0) / 100.0),
        )
