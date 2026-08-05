from __future__ import annotations

from django.utils import timezone
from rest_framework import serializers

from accounts.serializers import UserSerializer
from .models import (
    AgentExecution,
    Incident,
    ResolutionAction,
    ResolutionRecord,
    ReviewDecision,
    StatusEvent,
    TemporaryIncidentFile,
    WorkflowResult,
)


class WorkflowSerializer(serializers.ModelSerializer):
    progress_percent = serializers.SerializerMethodField()

    class Meta:
        model = WorkflowResult
        fields = (
            "current_stage",
            "progress_percent",
            "normalized_data",
            "severity_output",
            "root_cause_output",
            "runbook_output",
            "summary_output",
            "overall_confidence",
            "processing_time_seconds",
            "active_model",
            "is_processing",
            "failure_reason",
            "started_at",
            "completed_at",
        )

    def get_progress_percent(self, obj: WorkflowResult) -> int:
        stages = {
            WorkflowResult.Stage.NOT_STARTED: 0,
            WorkflowResult.Stage.NORMALIZATION: 16,
            WorkflowResult.Stage.SEVERITY: 33,
            WorkflowResult.Stage.ROOT_CAUSE: 50,
            WorkflowResult.Stage.RUNBOOK: 67,
            WorkflowResult.Stage.SUMMARY: 84,
            WorkflowResult.Stage.COMPLETE: 100,
        }
        return stages.get(obj.current_stage, 0)


class AgentExecutionSerializer(serializers.ModelSerializer):
    stage_label = serializers.CharField(source="get_stage_display", read_only=True)

    class Meta:
        model = AgentExecution
        fields = (
            "id",
            "stage",
            "stage_label",
            "status",
            "execution_mode",
            "model_name",
            "output",
            "confidence",
            "latency_ms",
            "retry_count",
            "error_message",
            "created_at",
        )


class ReviewDecisionSerializer(serializers.ModelSerializer):
    reviewer = UserSerializer(read_only=True)

    class Meta:
        model = ReviewDecision
        fields = ("id", "decision", "reviewer_note", "overrides", "reviewer", "decided_at")


class ResolutionActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResolutionAction
        fields = ("id", "order", "action", "result", "performed_by", "performed_at")


class ResolutionRecordSerializer(serializers.ModelSerializer):
    resolved_by = UserSerializer(read_only=True)
    actions = ResolutionActionSerializer(many=True, read_only=True)

    class Meta:
        model = ResolutionRecord
        fields = (
            "id",
            "resolution_summary",
            "confirmed_root_cause",
            "root_cause_confirmed",
            "verification_notes",
            "resolved_by",
            "started_at",
            "resolved_at",
            "actions",
        )


class StatusEventSerializer(serializers.ModelSerializer):
    changed_by = UserSerializer(read_only=True)

    class Meta:
        model = StatusEvent
        fields = ("id", "previous_status", "new_status", "note", "changed_by", "created_at")


class TemporaryIncidentFileSerializer(serializers.ModelSerializer):
    availability = serializers.CharField(read_only=True)
    has_expired = serializers.BooleanField(read_only=True)
    file_type_label = serializers.CharField(source="get_file_type_display", read_only=True)

    class Meta:
        model = TemporaryIncidentFile
        fields = (
            "id",
            "original_name",
            "content_type",
            "file_type",
            "file_type_label",
            "size_bytes",
            "sha256",
            "status",
            "availability",
            "has_expired",
            "retention_days",
            "uploaded_at",
            "expires_at",
            "deleted_at",
            "extracted_fields",
            "extracted_context",
            "information_gaps",
            "extraction_error",
        )
        read_only_fields = fields


class IncidentListSerializer(serializers.ModelSerializer):
    reference = serializers.CharField(read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    predicted_severity = serializers.SerializerMethodField()
    overall_confidence = serializers.SerializerMethodField()

    class Meta:
        model = Incident
        fields = (
            "id",
            "reference",
            "title",
            "service_name",
            "environment",
            "reported_severity",
            "predicted_severity",
            "status",
            "status_label",
            "overall_confidence",
            "submitted_at",
            "updated_at",
        )

    def get_predicted_severity(self, obj: Incident):
        workflow = getattr(obj, "workflow", None)
        return (workflow.severity_output or {}).get("level") if workflow else None

    def get_overall_confidence(self, obj: Incident):
        workflow = getattr(obj, "workflow", None)
        return workflow.overall_confidence if workflow else None


class IncidentCreateSerializer(serializers.ModelSerializer):
    source_file_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    extracted_context = serializers.JSONField(required=False, default=dict)
    information_gaps = serializers.JSONField(required=False, default=list)

    class Meta:
        model = Incident
        fields = (
            "title",
            "description",
            "service_name",
            "environment",
            "reported_severity",
            "business_impact",
            "source_file_id",
            "extracted_context",
            "information_gaps",
        )

    def validate_source_file_id(self, value):
        if not value:
            return value
        request = self.context["request"]
        try:
            source_file = TemporaryIncidentFile.objects.get(id=value, uploaded_by=request.user)
        except TemporaryIncidentFile.DoesNotExist as exc:
            raise serializers.ValidationError("The temporary source file was not found.") from exc
        if source_file.incident_id:
            raise serializers.ValidationError("This source file is already attached to an incident.")
        if source_file.status == TemporaryIncidentFile.Status.DELETED or source_file.deleted_at:
            raise serializers.ValidationError("This source file has already been deleted.")
        if source_file.expires_at <= timezone.now():
            raise serializers.ValidationError("This source file has expired. Upload it again.")
        return value

    def create(self, validated_data):
        request = self.context["request"]
        source_file_id = validated_data.pop("source_file_id", None)
        source_file = None
        if source_file_id:
            source_file = TemporaryIncidentFile.objects.get(id=source_file_id, uploaded_by=request.user)

        source = source_file.file_type if source_file else "manual"
        raw_input = {
            key: value
            for key, value in validated_data.items()
            if key not in {"extracted_context", "information_gaps"}
        }
        incident = Incident.objects.create(
            **validated_data,
            submitted_by=request.user,
            source=source,
            raw_input=raw_input,
        )
        if source_file:
            source_file.incident = incident
            source_file.save(update_fields=("incident",))
        WorkflowResult.objects.create(incident=incident)
        StatusEvent.objects.create(
            incident=incident,
            previous_status="",
            new_status=Incident.Status.SUBMITTED,
            note=(
                f"Incident created from temporary {source_file.get_file_type_display()} source."
                if source_file
                else "Incident submitted."
            ),
            changed_by=request.user,
        )
        return incident


class IncidentDetailSerializer(serializers.ModelSerializer):
    reference = serializers.CharField(read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    submitted_by = UserSerializer(read_only=True)
    workflow = WorkflowSerializer(read_only=True)
    agent_executions = AgentExecutionSerializer(many=True, read_only=True)
    reviews = ReviewDecisionSerializer(many=True, read_only=True)
    status_events = StatusEventSerializer(many=True, read_only=True)
    resolution = serializers.SerializerMethodField()
    source_file = serializers.SerializerMethodField()

    class Meta:
        model = Incident
        fields = (
            "id",
            "reference",
            "title",
            "description",
            "service_name",
            "environment",
            "source",
            "reported_severity",
            "business_impact",
            "extracted_context",
            "information_gaps",
            "source_file",
            "status",
            "status_label",
            "submitted_by",
            "submitted_at",
            "updated_at",
            "resolved_at",
            "reopened_count",
            "workflow",
            "agent_executions",
            "reviews",
            "resolution",
            "status_events",
        )

    def get_resolution(self, obj: Incident):
        try:
            resolution = obj.resolution
        except ResolutionRecord.DoesNotExist:
            return None
        return ResolutionRecordSerializer(resolution).data

    def get_source_file(self, obj: Incident):
        source_file = next(iter(obj.temporary_files.all()), None)
        return TemporaryIncidentFileSerializer(source_file).data if source_file else None


class ReviewInputSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=ReviewDecision.Decision.choices)
    reviewer_note = serializers.CharField(required=False, allow_blank=True)
    overrides = serializers.JSONField(required=False, default=dict)


class ResolutionActionInputSerializer(serializers.Serializer):
    order = serializers.IntegerField(min_value=1)
    action = serializers.CharField()
    result = serializers.CharField(required=False, allow_blank=True)
    performed_by = serializers.CharField(required=False, allow_blank=True)
    performed_at = serializers.DateTimeField(required=False, allow_null=True)


class ResolveInputSerializer(serializers.Serializer):
    resolution_summary = serializers.CharField()
    confirmed_root_cause = serializers.CharField()
    root_cause_confirmed = serializers.BooleanField(default=True)
    verification_notes = serializers.CharField()
    actions = ResolutionActionInputSerializer(many=True, min_length=1)


class ReopenInputSerializer(serializers.Serializer):
    reason = serializers.CharField(min_length=8)
