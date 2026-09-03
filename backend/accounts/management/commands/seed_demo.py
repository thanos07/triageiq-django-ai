from __future__ import annotations

import json
import os
from datetime import timedelta
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
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


_DATA_PATH = (
    Path(__file__).resolve().parents[3]
    / "ai_engine"
    / "data"
    / "demo_incidents.json"
)

# The public demo account must never become an application administrator.
SAFE_DEMO_ROLES = {
    User.Role.VIEWER,
    User.Role.INCIDENT_MANAGER,
    User.Role.REVIEWER,
}


class Command(BaseCommand):
    help = (
        "Create a restricted demo account and "
        "20 synthetic incident conditions."
    )

    @staticmethod
    def _env_bool(
        name: str,
        default: bool = False,
    ) -> bool:
        """
        Convert an environment variable into a Boolean value.
        """

        default_value = "true" if default else "false"
        value = os.getenv(name, default_value)

        return value.strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

    def _load_scenarios(self) -> list[dict]:
        """
        Load and validate the 20 synthetic incident scenarios.
        """

        with _DATA_PATH.open(
            "r",
            encoding="utf-8",
        ) as handle:
            scenarios = json.load(handle)

        if (
            not isinstance(scenarios, list)
            or len(scenarios) != 20
        ):
            raise ValueError(
                "demo_incidents.json must contain "
                "exactly 20 scenarios."
            )

        return scenarios

    def _prepare_demo_user(self) -> User:
        """
        Create or update the public demo account.

        The account is explicitly prevented from receiving Django Admin
        or application-administrator privileges.
        """

        email = os.getenv(
            "DEMO_EMAIL",
            "demo@triageiq.dev",
        ).strip().lower()

        password = os.getenv(
            "DEMO_PASSWORD",
            "DemoPass123!",
        )

        username = os.getenv(
            "DEMO_USERNAME",
            "triageiq-demo",
        ).strip()

        role = os.getenv(
            "DEMO_ROLE",
            User.Role.VIEWER,
        ).strip().lower()

        if not email:
            raise CommandError(
                "DEMO_EMAIL must not be empty."
            )

        if not password:
            raise CommandError(
                "DEMO_PASSWORD must not be empty."
            )

        if not username:
            raise CommandError(
                "DEMO_USERNAME must not be empty."
            )

        if role not in SAFE_DEMO_ROLES:
            allowed_roles = ", ".join(
                sorted(SAFE_DEMO_ROLES)
            )

            raise CommandError(
                "DEMO_ROLE must be one of: "
                f"{allowed_roles}. "
                "The demo account cannot be assigned "
                "the administrator role."
            )

        user = User.objects.filter(
            email__iexact=email,
        ).first()

        # Never convert a real Django superuser into a demo account.
        if user is not None and user.is_superuser:
            raise CommandError(
                "The configured DEMO_EMAIL belongs to a "
                "Django superuser. Use a different demo email."
            )

        username_conflict = User.objects.filter(
            username=username,
        )

        if user is not None:
            username_conflict = username_conflict.exclude(
                pk=user.pk
            )

        if username_conflict.exists():
            raise CommandError(
                f"The username '{username}' is already used "
                "by another account. Configure a different "
                "DEMO_USERNAME."
            )

        if user is None:
            user = User(
                email=email,
                username=username,
            )

        user.email = email
        user.username = username
        user.first_name = "Demo"
        user.last_name = "Operator"
        user.role = role

        # Public demo accounts must never access Django Admin.
        user.is_staff = False
        user.is_superuser = False
        user.is_active = True

        user.set_password(password)
        user.save()

        return user

    @staticmethod
    def _complete_pipeline(
        incident: Incident,
        user: User,
    ) -> Incident:
        """
        Run every AI pipeline stage for a synthetic incident.
        """

        for _ in range(6):
            incident, _workflow, stage = advance_pipeline(
                incident,
                user=user,
            )

            if stage == "complete":
                return incident

        return Incident.objects.get(
            pk=incident.pk,
        )

    @staticmethod
    def _approve(
        incident: Incident,
        user: User,
        note: str,
    ) -> Incident:
        """
        Create a synthetic approval and move the incident forward.
        """

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

    def _apply_target_state(
        self,
        incident: Incident,
        scenario: dict,
        user: User,
    ) -> None:
        """
        Move a synthetic incident into its configured demonstration state.
        """

        target = scenario.get(
            "target_state",
            "awaiting_review",
        )

        expected_runbook = scenario.get(
            "expected_runbook_id",
            "",
        )

        incident = self._complete_pipeline(
            incident,
            user,
        )

        workflow = WorkflowResult.objects.get(
            incident=incident,
        )

        actual_runbook = (
            workflow.runbook_output or {}
        ).get("matched_case_id")

        if actual_runbook != expected_runbook:
            self.stderr.write(
                self.style.WARNING(
                    f"{scenario.get('slug')}: "
                    f"expected {expected_runbook}, "
                    f"matched {actual_runbook or 'none'}"
                )
            )

        if target == "awaiting_review":
            return

        if target in {
            "revision_required",
            "rejected",
        }:
            decision = (
                ReviewDecision.Decision.REVISION_REQUIRED
                if target == "revision_required"
                else ReviewDecision.Decision.REJECTED
            )

            reviewer_note = (
                "Synthetic reviewer requested stronger "
                "diagnostic evidence before approval."
                if target == "revision_required"
                else
                "Synthetic reviewer rejected the proposed "
                "response pending service-owner correction."
            )

            ReviewDecision.objects.create(
                incident=incident,
                reviewer=user,
                decision=decision,
                reviewer_note=reviewer_note,
            )

            transition_incident(
                incident,
                target,
                user=user,
                note=(
                    "Synthetic demo moved to "
                    f"{target.replace('_', ' ')}."
                ),
            )

            return

        incident = self._approve(
            incident,
            user,
            (
                "Synthetic reviewer approved the matched "
                "runbook for demonstration."
            ),
        )

        resolution = ResolutionRecord.objects.create(
            incident=incident,
            resolved_by=user,
        )

        incident = transition_incident(
            incident,
            Incident.Status.REMEDIATION_IN_PROGRESS,
            user=user,
            note=(
                "Synthetic remediation started from "
                "the matched runbook."
            ),
        )

        runbook = workflow.runbook_output or {}
        steps = runbook.get("steps", []) or []

        first_action = next(
            (
                str(item.get("action"))
                for item in steps
                if isinstance(item, dict)
                and item.get("action")
            ),
            (
                "Applied the safest reversible mitigation "
                "from the matched runbook."
            ),
        )

        ResolutionAction.objects.create(
            resolution=resolution,
            order=1,
            action=first_action,
            result=(
                "Mitigation is in progress and awaiting "
                "final verification."
                if target == "remediation_in_progress"
                else
                "The primary failure signal returned "
                "to baseline."
            ),
            performed_by=(
                user.get_full_name()
                or user.email
            ),
            performed_at=(
                timezone.now()
                - timedelta(minutes=4)
            ),
        )

        if target == "remediation_in_progress":
            return

        resolution.resolution_summary = (
            "Synthetic resolution completed using "
            f"{runbook.get('matched_case_name', expected_runbook)}."
        )

        resolution.confirmed_root_cause = (
            (
                workflow.root_cause_output
                or {}
            ).get("probable_cause")
            or scenario.get(
                "title",
                "Synthetic incident cause",
            )
        )

        resolution.root_cause_confirmed = True

        resolution.verification_notes = (
            "Health checks, error rate, latency, and the "
            "affected user journey remained healthy during "
            "the synthetic observation window."
        )

        resolution.resolved_at = timezone.now()
        resolution.save()

        transition_incident(
            incident,
            Incident.Status.RESOLVED,
            user=user,
            note=(
                "Synthetic recovery evidence passed and "
                "the incident was resolved."
            ),
        )

    def handle(
        self,
        *args,
        **options,
    ) -> None:
        """
        Create the restricted user and synthetic incident dataset.
        """

        user = self._prepare_demo_user()
        scenarios = self._load_scenarios()

        created_count = 0

        for scenario in scenarios:
            incident, created = Incident.objects.get_or_create(
                title=scenario["title"],
                defaults={
                    "description": scenario["description"],
                    "service_name": scenario["service_name"],
                    "environment": scenario["environment"],
                    "reported_severity": (
                        scenario["reported_severity"]
                    ),
                    "business_impact": (
                        scenario["business_impact"]
                    ),
                    "source": "synthetic-seed",
                    "raw_input": {
                        "synthetic_condition": (
                            scenario["slug"]
                        ),
                        "expected_runbook_id": (
                            scenario["expected_runbook_id"]
                        ),
                    },
                    "submitted_by": user,
                },
            )

            WorkflowResult.objects.get_or_create(
                incident=incident,
            )

            if not created:
                continue

            created_count += 1

            StatusEvent.objects.create(
                incident=incident,
                previous_status="",
                new_status=Incident.Status.SUBMITTED,
                note=(
                    "Synthetic demonstration incident. "
                    "Expected runbook: "
                    f"{scenario['expected_runbook_id']}."
                ),
                changed_by=user,
            )

            self._apply_target_state(
                incident,
                scenario,
                user,
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Demo data is ready: "
                f"{len(scenarios)} synthetic conditions "
                f"({created_count} newly created)."
            )
        )

        self.stdout.write(
            "Runbook knowledge base: "
            "30 problem-solution cases."
        )

        self.stdout.write(
            f"Demo email: {user.email}"
        )

        self.stdout.write(
            f"Demo role: {user.role}"
        )

        self.stdout.write(
            "Django Admin access: disabled"
        )

        if self._env_bool(
            "DEMO_PRINT_PASSWORD",
            default=False,
        ):
            self.stdout.write(
                "Demo password: "
                f"{os.getenv('DEMO_PASSWORD', 'DemoPass123!')}"
            )
        else:
            self.stdout.write(
                "Demo password was not printed. "
                "It is configured through DEMO_PASSWORD."
            )