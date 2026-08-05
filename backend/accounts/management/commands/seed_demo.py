from __future__ import annotations

import json
import os
from datetime import timedelta
from pathlib import Path

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import User
from ai_engine.pipeline import advance_pipeline
from incidents.models import (
    Incident,
    ResolutionAction,
    ResolutionRecord,
    ReviewDecision,
    StatusEvent,
    WorkflowResult,
)
from incidents.services.lifecycle import transition_incident

_DATA_PATH = Path(__file__).resolve().parents[3] / "ai_engine" / "data" / "demo_incidents.json"


class Command(BaseCommand):
    help = "Create a demo administrator and 20 synthetic incident conditions."

    def _load_scenarios(self) -> list[dict]:
        with _DATA_PATH.open("r", encoding="utf-8") as handle:
            scenarios = json.load(handle)
        if not isinstance(scenarios, list) or len(scenarios) != 20:
            raise ValueError("demo_incidents.json must contain exactly 20 scenarios")
        return scenarios

    @staticmethod
    def _complete_pipeline(incident: Incident, user: User) -> Incident:
        for _ in range(5):
            incident, workflow, stage = advance_pipeline(incident, user=user)
            if stage == "complete":
                return incident
        return Incident.objects.get(pk=incident.pk)

    @staticmethod
    def _approve(incident: Incident, user: User, note: str) -> Incident:
        ReviewDecision.objects.create(
            incident=incident,
            reviewer=user,
            decision=ReviewDecision.Decision.APPROVED,
            reviewer_note=note,
        )
        return transition_incident(
            incident,
            Incident.Status.APPROVED,
            user=user,
            note=note,
        )

    def _apply_target_state(self, incident: Incident, scenario: dict, user: User) -> None:
        target = scenario.get("target_state", "awaiting_review")
        expected = scenario.get("expected_runbook_id", "")
        incident = self._complete_pipeline(incident, user)
        workflow = WorkflowResult.objects.get(incident=incident)
        actual = (workflow.runbook_output or {}).get("matched_case_id")
        if actual != expected:
            self.stderr.write(
                self.style.WARNING(
                    f"{scenario.get('slug')}: expected {expected}, matched {actual or 'none'}"
                )
            )

        if target == "awaiting_review":
            return

        if target in {"revision_required", "rejected"}:
            decision = (
                ReviewDecision.Decision.REVISION_REQUIRED
                if target == "revision_required"
                else ReviewDecision.Decision.REJECTED
            )
            ReviewDecision.objects.create(
                incident=incident,
                reviewer=user,
                decision=decision,
                reviewer_note=(
                    "Synthetic reviewer requested stronger diagnostic evidence before approval."
                    if target == "revision_required"
                    else "Synthetic reviewer rejected the proposed response pending service-owner correction."
                ),
            )
            transition_incident(
                incident,
                target,
                user=user,
                note=f"Synthetic demo moved to {target.replace('_', ' ')}.",
            )
            return

        incident = self._approve(
            incident,
            user,
            "Synthetic reviewer approved the matched runbook for demonstration.",
        )
        record = ResolutionRecord.objects.create(incident=incident, resolved_by=user)
        incident = transition_incident(
            incident,
            Incident.Status.REMEDIATION_IN_PROGRESS,
            user=user,
            note="Synthetic remediation started from the matched runbook.",
        )
        runbook = workflow.runbook_output or {}
        steps = runbook.get("steps", []) or []
        first_action = next(
            (str(item.get("action")) for item in steps if isinstance(item, dict) and item.get("action")),
            "Applied the safest reversible mitigation from the matched runbook.",
        )
        ResolutionAction.objects.create(
            resolution=record,
            order=1,
            action=first_action,
            result=(
                "Mitigation is in progress and awaiting final verification."
                if target == "remediation_in_progress"
                else "The primary failure signal returned to baseline."
            ),
            performed_by=user.get_full_name() or user.email,
            performed_at=timezone.now() - timedelta(minutes=4),
        )

        if target == "remediation_in_progress":
            return

        record.resolution_summary = (
            f"Synthetic resolution completed using {runbook.get('matched_case_name', expected)}."
        )
        record.confirmed_root_cause = (
            (workflow.root_cause_output or {}).get("probable_cause")
            or scenario.get("title", "Synthetic incident cause")
        )
        record.root_cause_confirmed = True
        record.verification_notes = (
            "Health checks, error rate, latency, and the affected user journey remained healthy "
            "during the synthetic observation window."
        )
        record.resolved_at = timezone.now()
        record.save()
        transition_incident(
            incident,
            Incident.Status.RESOLVED,
            user=user,
            note="Synthetic recovery evidence passed and the incident was resolved.",
        )

    def handle(self, *args, **options):
        email = os.getenv("DEMO_EMAIL", "demo@triageiq.dev")
        password = os.getenv("DEMO_PASSWORD", "DemoPass123!")
        user, _ = User.objects.get_or_create(
            email=email,
            defaults={
                "username": "triageiq-demo",
                "first_name": "Demo",
                "last_name": "Operator",
                "role": User.Role.ADMIN,
                "is_staff": True,
            },
        )
        user.role = User.Role.ADMIN
        user.is_staff = True
        user.set_password(password)
        user.save()

        created_count = 0
        scenarios = self._load_scenarios()
        for scenario in scenarios:
            incident, created = Incident.objects.get_or_create(
                title=scenario["title"],
                defaults={
                    "description": scenario["description"],
                    "service_name": scenario["service_name"],
                    "environment": scenario["environment"],
                    "reported_severity": scenario["reported_severity"],
                    "business_impact": scenario["business_impact"],
                    "source": "synthetic-seed",
                    "raw_input": {
                        "synthetic_condition": scenario["slug"],
                        "expected_runbook_id": scenario["expected_runbook_id"],
                    },
                    "submitted_by": user,
                },
            )
            WorkflowResult.objects.get_or_create(incident=incident)
            if not created:
                continue
            created_count += 1
            StatusEvent.objects.create(
                incident=incident,
                previous_status="",
                new_status=Incident.Status.SUBMITTED,
                note=(
                    "Synthetic demonstration incident. Expected runbook: "
                    f"{scenario['expected_runbook_id']}."
                ),
                changed_by=user,
            )
            self._apply_target_state(incident, scenario, user)

        self.stdout.write(
            self.style.SUCCESS(
                f"Demo data is ready: {len(scenarios)} synthetic conditions "
                f"({created_count} newly created)."
            )
        )
        self.stdout.write("Runbook knowledge base: 30 problem–solution cases.")
        self.stdout.write(f"Email: {email}")
        self.stdout.write(f"Password: {password}")
