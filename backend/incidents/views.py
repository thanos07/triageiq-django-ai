from __future__ import annotations

from datetime import timedelta

from django.db import transaction
from django.db.models import Avg, Count, Q
from django.http import FileResponse
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ai_engine.pipeline import advance_pipeline
from ai_engine.runbook_knowledge import load_runbook_cases
from reports.pdf import build_incident_pdf
from .models import (
    Incident,
    ResolutionAction,
    ResolutionRecord,
    ReviewDecision,
    StatusEvent,
    TemporaryIncidentFile,
    WorkflowResult,
)
from .permissions import IsIncidentManager, IsReviewer
from .serializers import (
    IncidentCreateSerializer,
    IncidentDetailSerializer,
    IncidentListSerializer,
    ReopenInputSerializer,
    ResolveInputSerializer,
    ReviewInputSerializer,
    TemporaryIncidentFileSerializer,
)
from .services.lifecycle import transition_incident
from .services.temporary_storage import TemporaryStorageError, storage
from .services.upload_extraction import (
    UploadExtractionError,
    extract_from_bytes,
    process_uploaded_file,
)


class DashboardView(APIView):
    def get(self, request):
        queryset = Incident.objects.all()
        counts = queryset.aggregate(
            total=Count("id"),
            open=Count("id", filter=~Q(status__in=[Incident.Status.RESOLVED, Incident.Status.CLOSED])),
            awaiting_review=Count("id", filter=Q(status=Incident.Status.AWAITING_REVIEW)),
            critical=Count("id", filter=Q(workflow__severity_output__level="critical")),
            resolved=Count("id", filter=Q(status__in=[Incident.Status.RESOLVED, Incident.Status.CLOSED])),
            average_confidence=Avg("workflow__overall_confidence"),
        )
        recent = queryset.select_related("workflow", "submitted_by")[:6]
        severity_counts = {
            level: queryset.filter(workflow__severity_output__level=level).count()
            for level in ("critical", "high", "medium", "low")
        }
        return Response({
            **counts,
            "average_confidence": round(counts["average_confidence"] or 0, 3),
            "severity_counts": severity_counts,
            "recent_incidents": IncidentListSerializer(recent, many=True).data,
        })


class RunbookLibraryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = str(request.query_params.get("q", "")).strip().lower()
        category = str(request.query_params.get("category", "")).strip().lower()
        cases = list(load_runbook_cases())
        if category:
            cases = [item for item in cases if str(item.get("category", "")).lower() == category]
        if query:
            cases = [
                item for item in cases
                if query in " ".join([
                    str(item.get("id", "")),
                    str(item.get("name", "")),
                    str(item.get("problem", "")),
                    str(item.get("category", "")),
                    " ".join(str(value) for value in item.get("keywords", []) or []),
                ]).lower()
            ]
        categories = sorted({str(item.get("category", "")) for item in load_runbook_cases() if item.get("category")})
        return Response({
            "count": len(cases),
            "total": len(load_runbook_cases()),
            "categories": categories,
            "results": cases,
        })


class IncidentViewSet(viewsets.ModelViewSet):
    http_method_names = ["get", "post", "head", "options"]
    queryset = Incident.objects.select_related("workflow", "submitted_by").prefetch_related(
        "agent_executions__tool_executions",
        "reviews__reviewer",
        "status_events__changed_by",
        "resolution__actions",
        "temporary_files",
    )
    filterset_fields = ("status", "environment", "reported_severity", "service_name")
    search_fields = ("title", "description", "service_name")
    ordering_fields = ("submitted_at", "updated_at", "service_name")
    ordering = ("-submitted_at",)

    def get_serializer_class(self):
        if self.action == "create":
            return IncidentCreateSerializer
        if self.action == "list":
            return IncidentListSerializer
        return IncidentDetailSerializer

    def get_permissions(self):
        manager_actions = {
            "create",
            "advance",
            "start_resolution",
            "resolve",
            "reopen",
            "close",
            "demo",
            "extract_upload",
            "reextract_source_file",
            "delete_source_file",
        }
        if self.action in manager_actions:
            permission_classes = [IsIncidentManager]
        elif self.action == "review":
            permission_classes = [IsReviewer]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        incident = serializer.save()
        refreshed = self.get_queryset().get(pk=incident.pk)
        return Response(
            IncidentDetailSerializer(refreshed, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=False,
        methods=["post"],
        url_path="extract-upload",
        parser_classes=[MultiPartParser, FormParser],
    )
    def extract_upload(self, request):
        uploaded_file = request.FILES.get("file")
        if not uploaded_file:
            raise ValidationError("Select a PDF, JSON, CSV, TXT, or LOG file.")
        try:
            retention_days = int(request.data.get("retention_days", 10))
        except (TypeError, ValueError) as exc:
            raise ValidationError("Retention must be either 7 or 10 days.") from exc

        try:
            result, metadata = process_uploaded_file(uploaded_file, retention_days=retention_days)
        except (UploadExtractionError, TemporaryStorageError) as exc:
            raise ValidationError(str(exc)) from exc

        expires_at = timezone.now() + timedelta(days=retention_days)
        try:
            source_file = TemporaryIncidentFile.objects.create(
                uploaded_by=request.user,
                original_name=metadata["original_name"],
                storage_key=metadata["storage_key"],
                content_type=metadata["content_type"],
                file_type=result.file_type,
                size_bytes=metadata["size_bytes"],
                sha256=metadata["sha256"],
                status=TemporaryIncidentFile.Status.READY,
                extracted_fields=result.fields,
                extracted_context=result.extracted_context,
                information_gaps=result.information_gaps,
                retention_days=retention_days,
                expires_at=expires_at,
            )
        except Exception:
            try:
                storage.delete(metadata["storage_key"])
            except TemporaryStorageError:
                pass
            raise

        return Response({
            "source_file": TemporaryIncidentFileSerializer(source_file).data,
            "fields": result.fields,
            "extracted_context": result.extracted_context,
            "information_gaps": result.information_gaps,
            "warnings": result.warnings,
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="source-file/reextract")
    def reextract_source_file(self, request, pk=None):
        incident = self.get_object()
        source_file = self._active_source_file(incident)
        try:
            payload = storage.get(source_file.storage_key)
            result = extract_from_bytes(
                payload=payload,
                filename=source_file.original_name,
                content_type=source_file.content_type,
            )
        except (TemporaryStorageError, UploadExtractionError) as exc:
            raise ValidationError(str(exc)) from exc

        source_file.extracted_fields = result.fields
        source_file.extracted_context = result.extracted_context
        source_file.information_gaps = result.information_gaps
        source_file.extraction_error = ""
        source_file.status = TemporaryIncidentFile.Status.READY
        source_file.save(update_fields=(
            "extracted_fields",
            "extracted_context",
            "information_gaps",
            "extraction_error",
            "status",
        ))
        incident.extracted_context = result.extracted_context
        incident.information_gaps = result.information_gaps
        incident.save(update_fields=("extracted_context", "information_gaps", "updated_at"))
        StatusEvent.objects.create(
            incident=incident,
            previous_status=incident.status,
            new_status=incident.status,
            note="Temporary source document was re-extracted; user-edited incident fields were preserved.",
            changed_by=request.user,
        )
        return Response({
            "source_file": TemporaryIncidentFileSerializer(source_file).data,
            "fields": result.fields,
            "extracted_context": result.extracted_context,
            "information_gaps": result.information_gaps,
            "warnings": result.warnings,
        })

    @action(detail=True, methods=["post"], url_path="source-file/delete")
    def delete_source_file(self, request, pk=None):
        incident = self.get_object()
        source_file = next(iter(incident.temporary_files.all()), None)
        if not source_file:
            raise ValidationError("This incident has no temporary source file.")
        if source_file.status != TemporaryIncidentFile.Status.DELETED:
            try:
                storage.delete(source_file.storage_key)
            except TemporaryStorageError as exc:
                if not source_file.has_expired:
                    raise ValidationError(str(exc)) from exc
            source_file.status = TemporaryIncidentFile.Status.DELETED
            source_file.deleted_at = timezone.now()
            source_file.save(update_fields=("status", "deleted_at"))
            StatusEvent.objects.create(
                incident=incident,
                previous_status=incident.status,
                new_status=incident.status,
                note="Temporary source document deleted. Extracted incident data was retained.",
                changed_by=request.user,
            )
        return Response(TemporaryIncidentFileSerializer(source_file).data)

    def _active_source_file(self, incident: Incident) -> TemporaryIncidentFile:
        source_file = next(iter(incident.temporary_files.all()), None)
        if not source_file:
            raise ValidationError("This incident has no temporary source file.")
        if source_file.status == TemporaryIncidentFile.Status.DELETED or source_file.deleted_at:
            raise ValidationError("The temporary source file has been deleted.")
        if source_file.has_expired:
            raise ValidationError("The temporary source file has expired.")
        return source_file

    @action(detail=True, methods=["post"])
    def advance(self, request, pk=None):
        incident = self.get_object()
        incident, workflow, completed_stage = advance_pipeline(incident, user=request.user)
        refreshed = self.get_queryset().get(pk=incident.pk)
        return Response({
            "completed_stage": completed_stage,
            "incident": IncidentDetailSerializer(refreshed, context={"request": request}).data,
        })

    @action(detail=True, methods=["post"])
    def review(self, request, pk=None):
        incident = self.get_object()
        if incident.status != Incident.Status.AWAITING_REVIEW:
            raise ValidationError("This incident is not awaiting review.")
        serializer = ReviewInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        with transaction.atomic():
            ReviewDecision.objects.create(
                incident=incident,
                reviewer=request.user,
                decision=data["decision"],
                reviewer_note=data.get("reviewer_note", ""),
                overrides=data.get("overrides", {}),
            )
            workflow = incident.workflow
            overrides = data.get("overrides", {})
            if overrides.get("severity") and workflow.severity_output:
                workflow.severity_output = {**workflow.severity_output, "level": overrides["severity"]}
                workflow.save(update_fields=("severity_output", "updated_at"))

            incident = transition_incident(
                incident,
                data["decision"],
                user=request.user,
                note=data.get("reviewer_note", "") or f"AI triage {data['decision'].replace('_', ' ')}.",
            )

            if data["decision"] == ReviewDecision.Decision.REVISION_REQUIRED:
                workflow.current_stage = WorkflowResult.Stage.NORMALIZATION
                workflow.severity_output = None
                workflow.investigation_output = None
                workflow.root_cause_output = None
                workflow.runbook_output = None
                workflow.summary_output = None
                workflow.overall_confidence = None
                workflow.completed_at = None
                workflow.save()

        refreshed = self.get_queryset().get(pk=incident.pk)
        return Response(IncidentDetailSerializer(refreshed).data)

    @action(detail=True, methods=["post"], url_path="start-resolution")
    def start_resolution(self, request, pk=None):
        incident = self.get_object()
        if incident.status != Incident.Status.APPROVED:
            raise ValidationError("Only an approved incident can enter remediation.")
        ResolutionRecord.objects.get_or_create(incident=incident, defaults={"resolved_by": request.user})
        incident = transition_incident(
            incident,
            Incident.Status.REMEDIATION_IN_PROGRESS,
            user=request.user,
            note="Remediation work started.",
        )
        return Response(IncidentDetailSerializer(self.get_queryset().get(pk=incident.pk)).data)

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        incident = self.get_object()
        if incident.status != Incident.Status.REMEDIATION_IN_PROGRESS:
            raise ValidationError("The incident must be in remediation before it can be resolved.")
        serializer = ResolveInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        with transaction.atomic():
            resolution, _ = ResolutionRecord.objects.get_or_create(
                incident=incident,
                defaults={"resolved_by": request.user},
            )
            resolution.resolution_summary = data["resolution_summary"]
            resolution.confirmed_root_cause = data["confirmed_root_cause"]
            resolution.root_cause_confirmed = data["root_cause_confirmed"]
            resolution.verification_notes = data["verification_notes"]
            resolution.resolved_by = request.user
            resolution.resolved_at = timezone.now()
            resolution.save()
            resolution.actions.all().delete()
            ResolutionAction.objects.bulk_create([
                ResolutionAction(resolution=resolution, **action)
                for action in data["actions"]
            ])
            incident = transition_incident(
                incident,
                Incident.Status.RESOLVED,
                user=request.user,
                note="Recovery verified and incident marked resolved.",
            )

        return Response(IncidentDetailSerializer(self.get_queryset().get(pk=incident.pk)).data)

    @action(detail=True, methods=["post"])
    def reopen(self, request, pk=None):
        incident = self.get_object()
        if incident.status not in {Incident.Status.RESOLVED, Incident.Status.CLOSED}:
            raise ValidationError("Only a resolved or closed incident can be reopened.")
        serializer = ReopenInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        incident = transition_incident(
            incident,
            Incident.Status.REOPENED,
            user=request.user,
            note=serializer.validated_data["reason"],
        )
        workflow = incident.workflow
        workflow.current_stage = WorkflowResult.Stage.NORMALIZATION
        workflow.severity_output = None
        workflow.investigation_output = None
        workflow.root_cause_output = None
        workflow.runbook_output = None
        workflow.summary_output = None
        workflow.overall_confidence = None
        workflow.completed_at = None
        workflow.failure_reason = ""
        workflow.save()
        return Response(IncidentDetailSerializer(self.get_queryset().get(pk=incident.pk)).data)

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        incident = self.get_object()
        if incident.status != Incident.Status.RESOLVED:
            raise ValidationError("Only a resolved incident can be closed.")
        incident = transition_incident(
            incident,
            Incident.Status.CLOSED,
            user=request.user,
            note="Incident closed after observation period.",
        )
        return Response(IncidentDetailSerializer(self.get_queryset().get(pk=incident.pk)).data)

    @action(detail=True, methods=["get"])
    def report(self, request, pk=None):
        incident = self.get_object()
        draft = request.query_params.get("draft", "false").lower() == "true"
        if not draft and incident.status not in {Incident.Status.RESOLVED, Incident.Status.CLOSED}:
            raise ValidationError(
                "The final report is available only after resolution. Request ?draft=true for a draft report."
            )
        pdf = build_incident_pdf(incident, draft=draft)
        suffix = "draft-triage" if draft else "final-resolution"
        return FileResponse(
            pdf,
            as_attachment=True,
            filename=f"{incident.reference.lower()}-{suffix}.pdf",
            content_type="application/pdf",
        )

    @action(detail=False, methods=["post"])
    def demo(self, request):
        incident = Incident.objects.create(
            title="Checkout requests returning intermittent 502 errors",
            description=(
                "Customers in the production environment report failed checkout attempts. "
                "The issue started shortly after release 2026.08.05 and API gateway logs show intermittent 502 responses."
            ),
            service_name="checkout-api",
            environment=Incident.Environment.PRODUCTION,
            reported_severity=Incident.Severity.HIGH,
            business_impact="A portion of customers cannot complete purchases.",
            source="demo",
            submitted_by=request.user,
        )
        WorkflowResult.objects.create(incident=incident)
        StatusEvent.objects.create(
            incident=incident,
            previous_status="",
            new_status=Incident.Status.SUBMITTED,
            note="Demo incident created.",
            changed_by=request.user,
        )
        return Response(IncidentDetailSerializer(incident).data, status=status.HTTP_201_CREATED)
