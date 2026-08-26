from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class Incident(models.Model):
    class Environment(models.TextChoices):
        PRODUCTION = "production", "Production"
        STAGING = "staging", "Staging"
        DEVELOPMENT = "development", "Development"
        OTHER = "other", "Other"

    class Severity(models.TextChoices):
        CRITICAL = "critical", "Critical"
        HIGH = "high", "High"
        MEDIUM = "medium", "Medium"
        LOW = "low", "Low"
        UNKNOWN = "unknown", "Unknown"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        TRIAGING = "triaging", "AI triage in progress"
        AWAITING_REVIEW = "awaiting_review", "Awaiting human review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        REVISION_REQUIRED = "revision_required", "Revision required"
        REMEDIATION_IN_PROGRESS = "remediation_in_progress", "Remediation in progress"
        RESOLVED = "resolved", "Resolved"
        CLOSED = "closed", "Closed"
        FAILED = "failed", "Pipeline failed"
        REOPENED = "reopened", "Reopened"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=240)
    description = models.TextField()
    service_name = models.CharField(max_length=120)
    environment = models.CharField(
        max_length=24,
        choices=Environment.choices,
        default=Environment.PRODUCTION,
    )
    source = models.CharField(max_length=40, default="manual")
    reported_severity = models.CharField(
        max_length=16,
        choices=Severity.choices,
        default=Severity.UNKNOWN,
    )
    business_impact = models.TextField(blank=True)
    raw_input = models.JSONField(default=dict, blank=True)
    extracted_context = models.JSONField(default=dict, blank=True)
    information_gaps = models.JSONField(default=list, blank=True)
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.SUBMITTED,
        db_index=True,
    )
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="submitted_incidents",
    )
    submitted_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    reopened_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("-submitted_at",)
        indexes = [
            models.Index(fields=("status", "-submitted_at"), name="inc_status_submit_idx"),
            models.Index(fields=("service_name", "-submitted_at"), name="inc_service_submit_idx"),
        ]

    @property
    def reference(self) -> str:
        return f"INC-{str(self.id).split('-')[0].upper()}"

    def __str__(self) -> str:
        return f"{self.reference} · {self.title}"


class WorkflowResult(models.Model):
    class Stage(models.TextChoices):
        NOT_STARTED = "not_started", "Not started"
        NORMALIZATION = "normalization", "Normalization"
        SEVERITY = "severity", "Severity"
        INVESTIGATION = "investigation", "Investigation"
        ROOT_CAUSE = "root_cause", "Root cause"
        RUNBOOK = "runbook", "Runbook"
        SUMMARY = "summary", "Summary"
        COMPLETE = "complete", "Complete"

    incident = models.OneToOneField(
        Incident,
        on_delete=models.CASCADE,
        related_name="workflow",
    )
    current_stage = models.CharField(
        max_length=24,
        choices=Stage.choices,
        default=Stage.NOT_STARTED,
    )
    normalized_data = models.JSONField(null=True, blank=True)
    severity_output = models.JSONField(null=True, blank=True)
    investigation_output = models.JSONField(null=True, blank=True)
    root_cause_output = models.JSONField(null=True, blank=True)
    runbook_output = models.JSONField(null=True, blank=True)
    summary_output = models.JSONField(null=True, blank=True)
    overall_confidence = models.FloatField(null=True, blank=True)
    processing_time_seconds = models.FloatField(default=0)
    active_model = models.CharField(max_length=120, blank=True)
    is_processing = models.BooleanField(default=False)
    failure_reason = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Workflow for {self.incident.reference}: {self.current_stage}"


class AgentExecution(models.Model):
    class Stage(models.TextChoices):
        NORMALIZATION = "normalization", "Normalization"
        SEVERITY = "severity", "Severity agent"
        INVESTIGATION = "investigation", "Investigation agent"
        ROOT_CAUSE = "root_cause", "Root-cause agent"
        RUNBOOK = "runbook", "Runbook agent"
        SUMMARY = "summary", "Communication agent"

    class Status(models.TextChoices):
        STARTED = "started", "Started"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"

    class Mode(models.TextChoices):
        LIVE = "live", "Live model"
        MOCK = "mock", "Deterministic demo"
        FALLBACK = "fallback", "Deterministic fallback"

    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name="agent_executions")
    stage = models.CharField(max_length=24, choices=Stage.choices)
    status = models.CharField(max_length=16, choices=Status.choices)
    execution_mode = models.CharField(max_length=16, choices=Mode.choices, default=Mode.LIVE)
    model_name = models.CharField(max_length=120, blank=True)
    input_summary = models.JSONField(default=dict, blank=True)
    output = models.JSONField(default=dict, blank=True)
    confidence = models.FloatField(null=True, blank=True)
    latency_ms = models.PositiveIntegerField(null=True, blank=True)
    retry_count = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("created_at",)


class AgentToolExecution(models.Model):
    class Status(models.TextChoices):
        STARTED = "started", "Started"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"

    incident = models.ForeignKey(
        Incident,
        on_delete=models.CASCADE,
        related_name="tool_executions",
    )
    agent_execution = models.ForeignKey(
        AgentExecution,
        on_delete=models.CASCADE,
        related_name="tool_executions",
    )
    sequence = models.PositiveSmallIntegerField(default=1)
    tool_name = models.CharField(max_length=80)
    arguments = models.JSONField(default=dict, blank=True)
    result = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices)
    execution_mode = models.CharField(
        max_length=16,
        choices=AgentExecution.Mode.choices,
        default=AgentExecution.Mode.LIVE,
    )
    latency_ms = models.PositiveIntegerField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("agent_execution_id", "sequence", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("agent_execution", "sequence"),
                name="uniq_agent_tool_sequence",
            ),
        ]


class ReviewDecision(models.Model):
    class Decision(models.TextChoices):
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        REVISION_REQUIRED = "revision_required", "Revision required"

    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name="reviews")
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    decision = models.CharField(max_length=24, choices=Decision.choices)
    reviewer_note = models.TextField(blank=True)
    overrides = models.JSONField(default=dict, blank=True)
    decided_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-decided_at",)


class ResolutionRecord(models.Model):
    incident = models.OneToOneField(Incident, on_delete=models.CASCADE, related_name="resolution")
    resolution_summary = models.TextField(blank=True)
    confirmed_root_cause = models.TextField(blank=True)
    root_cause_confirmed = models.BooleanField(default=False)
    verification_notes = models.TextField(blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="resolved_incidents",
    )
    started_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)


class ResolutionAction(models.Model):
    resolution = models.ForeignKey(ResolutionRecord, on_delete=models.CASCADE, related_name="actions")
    order = models.PositiveIntegerField(default=1)
    action = models.TextField()
    result = models.TextField(blank=True)
    performed_by = models.CharField(max_length=160, blank=True)
    performed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("order", "id")


class StatusEvent(models.Model):
    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name="status_events")
    previous_status = models.CharField(max_length=32, blank=True)
    new_status = models.CharField(max_length=32)
    note = models.TextField(blank=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("created_at",)


class TemporaryIncidentFile(models.Model):
    class FileType(models.TextChoices):
        PDF = "pdf", "PDF"
        JSON = "json", "JSON"
        CSV = "csv", "CSV"
        TEXT = "text", "Text"
        LOG = "log", "Log"

    class Status(models.TextChoices):
        READY = "ready", "Ready"
        FAILED = "failed", "Extraction failed"
        DELETED = "deleted", "Deleted"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    incident = models.ForeignKey(
        Incident,
        on_delete=models.CASCADE,
        related_name="temporary_files",
        null=True,
        blank=True,
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="temporary_incident_files",
    )
    original_name = models.CharField(max_length=255)
    storage_key = models.CharField(max_length=500, unique=True)
    content_type = models.CharField(max_length=120)
    file_type = models.CharField(max_length=16, choices=FileType.choices)
    size_bytes = models.PositiveBigIntegerField()
    sha256 = models.CharField(max_length=64, db_index=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.READY)
    extracted_fields = models.JSONField(default=dict, blank=True)
    extracted_context = models.JSONField(default=dict, blank=True)
    information_gaps = models.JSONField(default=list, blank=True)
    extraction_error = models.TextField(blank=True)
    retention_days = models.PositiveSmallIntegerField(default=10)
    uploaded_at = models.DateTimeField(auto_now_add=True, db_index=True)
    expires_at = models.DateTimeField(db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-uploaded_at",)
        indexes = [
            models.Index(fields=("expires_at", "status"), name="temp_file_expiry_idx"),
        ]

    @property
    def has_expired(self) -> bool:
        return timezone.now() >= self.expires_at

    @property
    def availability(self) -> str:
        if self.status == self.Status.DELETED or self.deleted_at:
            return "deleted"
        if self.has_expired:
            return "expired"
        return self.status

    def __str__(self) -> str:
        return f"{self.original_name} · expires {self.expires_at.isoformat()}"
