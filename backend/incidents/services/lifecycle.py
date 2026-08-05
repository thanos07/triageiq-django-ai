from __future__ import annotations

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from incidents.models import Incident, StatusEvent


ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    Incident.Status.DRAFT: {Incident.Status.SUBMITTED},
    Incident.Status.SUBMITTED: {Incident.Status.TRIAGING},
    Incident.Status.TRIAGING: {Incident.Status.AWAITING_REVIEW, Incident.Status.FAILED},
    Incident.Status.AWAITING_REVIEW: {
        Incident.Status.APPROVED,
        Incident.Status.REJECTED,
        Incident.Status.REVISION_REQUIRED,
    },
    Incident.Status.REVISION_REQUIRED: {Incident.Status.TRIAGING},
    Incident.Status.REJECTED: {Incident.Status.TRIAGING},
    Incident.Status.APPROVED: {Incident.Status.REMEDIATION_IN_PROGRESS},
    Incident.Status.REMEDIATION_IN_PROGRESS: {Incident.Status.RESOLVED},
    Incident.Status.RESOLVED: {Incident.Status.CLOSED, Incident.Status.REOPENED},
    Incident.Status.REOPENED: {Incident.Status.TRIAGING},
    Incident.Status.FAILED: {Incident.Status.TRIAGING},
    Incident.Status.CLOSED: {Incident.Status.REOPENED},
}


@transaction.atomic
def transition_incident(
    incident: Incident,
    new_status: str,
    *,
    user=None,
    note: str = "",
    force: bool = False,
) -> Incident:
    current = Incident.objects.select_for_update().get(pk=incident.pk)
    if current.status == new_status:
        return current

    allowed = ALLOWED_TRANSITIONS.get(current.status, set())
    if not force and new_status not in allowed:
        raise ValidationError(
            {"status": f"Invalid transition from '{current.status}' to '{new_status}'."}
        )

    previous = current.status
    current.status = new_status
    if new_status == Incident.Status.RESOLVED:
        current.resolved_at = timezone.now()
    elif new_status == Incident.Status.REOPENED:
        current.resolved_at = None
        current.reopened_count += 1
    current.save(update_fields=("status", "resolved_at", "reopened_count", "updated_at"))

    StatusEvent.objects.create(
        incident=current,
        previous_status=previous,
        new_status=new_status,
        note=note,
        changed_by=user if getattr(user, "is_authenticated", False) else None,
    )
    return current
