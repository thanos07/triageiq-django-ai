from __future__ import annotations

import time
from typing import Any

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from ai_engine.agents import RootCauseAgent, RunbookAgent, SeverityAgent, SummaryAgent
from incidents.models import AgentExecution, Incident, WorkflowResult
from incidents.services.lifecycle import transition_incident


NEXT_STAGE = {
    WorkflowResult.Stage.NOT_STARTED: WorkflowResult.Stage.NORMALIZATION,
    WorkflowResult.Stage.NORMALIZATION: WorkflowResult.Stage.SEVERITY,
    WorkflowResult.Stage.SEVERITY: WorkflowResult.Stage.ROOT_CAUSE,
    WorkflowResult.Stage.ROOT_CAUSE: WorkflowResult.Stage.RUNBOOK,
    WorkflowResult.Stage.RUNBOOK: WorkflowResult.Stage.SUMMARY,
    WorkflowResult.Stage.SUMMARY: WorkflowResult.Stage.COMPLETE,
}


def _incident_context(incident: Incident) -> dict[str, Any]:
    return {
        "id": str(incident.id),
        "reference": incident.reference,
        "title": incident.title,
        "description": incident.description,
        "service_name": incident.service_name,
        "environment": incident.environment,
        "reported_severity": incident.reported_severity,
        "business_impact": incident.business_impact,
        "source": incident.source,
        "extracted_context": incident.extracted_context,
        "information_gaps": incident.information_gaps,
    }


def _confidence(data: dict[str, Any] | None) -> float | None:
    if not data:
        return None
    value = data.get("confidence")
    try:
        return min(1.0, max(0.0, float(value)))
    except (TypeError, ValueError):
        return None


def _aggregate_confidence(workflow: WorkflowResult) -> float:
    values = [
        _confidence(workflow.severity_output),
        _confidence(workflow.root_cause_output),
        _confidence(workflow.runbook_output),
        _confidence(workflow.summary_output),
    ]
    clean = [value for value in values if value is not None]
    return round(sum(clean) / len(clean), 4) if clean else 0.0


def _normalize(incident: Incident) -> dict[str, Any]:
    return {
        **_incident_context(incident),
        "title": " ".join(incident.title.split()),
        "description": " ".join(incident.description.split()),
        "service_name": " ".join(incident.service_name.split()),
    }


def _context_for(workflow: WorkflowResult, incident: Incident) -> dict[str, Any]:
    return {
        "incident": workflow.normalized_data or _incident_context(incident),
        "severity": workflow.severity_output or {},
        "root_cause": workflow.root_cause_output or {},
        "runbook": workflow.runbook_output or {},
    }


def advance_pipeline(incident: Incident, *, user=None) -> tuple[Incident, WorkflowResult, str]:
    workflow, _ = WorkflowResult.objects.get_or_create(incident=incident)

    if workflow.current_stage == WorkflowResult.Stage.COMPLETE:
        return incident, workflow, "complete"
    if incident.status in {
        Incident.Status.AWAITING_REVIEW,
        Incident.Status.APPROVED,
        Incident.Status.REMEDIATION_IN_PROGRESS,
        Incident.Status.RESOLVED,
        Incident.Status.CLOSED,
    }:
        raise ValidationError("AI triage is already complete for this incident.")
    if workflow.is_processing:
        raise ValidationError("Another pipeline stage is already running. Try again shortly.")

    if incident.status != Incident.Status.TRIAGING:
        incident = transition_incident(
            incident,
            Incident.Status.TRIAGING,
            user=user,
            note="AI triage started or resumed.",
        )

    with transaction.atomic():
        locked = WorkflowResult.objects.select_for_update().get(pk=workflow.pk)
        if locked.is_processing:
            raise ValidationError("Another pipeline stage is already running.")
        locked.is_processing = True
        locked.failure_reason = ""
        if locked.started_at is None:
            locked.started_at = timezone.now()
        locked.save(update_fields=("is_processing", "failure_reason", "started_at", "updated_at"))
        workflow = locked

    stage = NEXT_STAGE[workflow.current_stage]
    started = time.monotonic()

    try:
        if stage == WorkflowResult.Stage.NORMALIZATION:
            output = _normalize(incident)
            run_data = {
                "output": output,
                "model_name": "deterministic-normalizer-v1",
                "latency_ms": max(1, int((time.monotonic() - started) * 1000)),
                "retry_count": 0,
                "execution_mode": "mock",
                "error_message": "",
            }
        else:
            context = _context_for(workflow, incident)
            agents = {
                WorkflowResult.Stage.SEVERITY: SeverityAgent(),
                WorkflowResult.Stage.ROOT_CAUSE: RootCauseAgent(),
                WorkflowResult.Stage.RUNBOOK: RunbookAgent(),
                WorkflowResult.Stage.SUMMARY: SummaryAgent(),
            }
            run = agents[stage].run(context)
            run_data = {
                "output": run.output.model_dump(),
                "model_name": run.model_name,
                "latency_ms": run.latency_ms,
                "retry_count": run.retry_count,
                "execution_mode": run.execution_mode,
                "error_message": run.error_message,
            }

        with transaction.atomic():
            workflow = WorkflowResult.objects.select_for_update().get(pk=workflow.pk)
            field_map = {
                WorkflowResult.Stage.NORMALIZATION: "normalized_data",
                WorkflowResult.Stage.SEVERITY: "severity_output",
                WorkflowResult.Stage.ROOT_CAUSE: "root_cause_output",
                WorkflowResult.Stage.RUNBOOK: "runbook_output",
                WorkflowResult.Stage.SUMMARY: "summary_output",
            }
            setattr(workflow, field_map[stage], run_data["output"])
            workflow.current_stage = stage
            workflow.active_model = run_data["model_name"]
            workflow.processing_time_seconds += run_data["latency_ms"] / 1000
            workflow.is_processing = False
            workflow.save()

            AgentExecution.objects.create(
                incident=incident,
                stage=stage,
                status=AgentExecution.Status.SUCCESS,
                execution_mode=run_data["execution_mode"],
                model_name=run_data["model_name"],
                input_summary={"incident": incident.reference, "stage": stage},
                output=run_data["output"],
                confidence=_confidence(run_data["output"]),
                latency_ms=run_data["latency_ms"],
                retry_count=run_data["retry_count"],
                error_message=run_data["error_message"],
            )

            if stage == WorkflowResult.Stage.SUMMARY:
                workflow.current_stage = WorkflowResult.Stage.COMPLETE
                workflow.overall_confidence = _aggregate_confidence(workflow)
                workflow.completed_at = timezone.now()
                workflow.save(update_fields=(
                    "current_stage", "overall_confidence", "completed_at", "updated_at"
                ))
                incident = transition_incident(
                    incident,
                    Incident.Status.AWAITING_REVIEW,
                    user=user,
                    note="All AI agents completed. Human review is required.",
                )
                return incident, workflow, "complete"

        return incident, workflow, stage

    except Exception as exc:
        with transaction.atomic():
            workflow = WorkflowResult.objects.select_for_update().get(pk=workflow.pk)
            workflow.is_processing = False
            workflow.failure_reason = str(exc)
            workflow.save(update_fields=("is_processing", "failure_reason", "updated_at"))
            AgentExecution.objects.create(
                incident=incident,
                stage=stage,
                status=AgentExecution.Status.FAILED,
                execution_mode=AgentExecution.Mode.FALLBACK,
                model_name="",
                input_summary={"incident": incident.reference, "stage": stage},
                error_message=str(exc),
                latency_ms=max(1, int((time.monotonic() - started) * 1000)),
            )
        transition_incident(
            incident,
            Incident.Status.FAILED,
            user=user,
            note=f"Pipeline stage '{stage}' failed.",
        )
        raise
