# Generated for the standalone TriageIQ project.
import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Incident",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("title", models.CharField(max_length=240)),
                ("description", models.TextField()),
                ("service_name", models.CharField(max_length=120)),
                ("environment", models.CharField(choices=[("production", "Production"), ("staging", "Staging"), ("development", "Development"), ("other", "Other")], default="production", max_length=24)),
                ("source", models.CharField(default="manual", max_length=40)),
                ("reported_severity", models.CharField(choices=[("critical", "Critical"), ("high", "High"), ("medium", "Medium"), ("low", "Low"), ("unknown", "Unknown")], default="unknown", max_length=16)),
                ("business_impact", models.TextField(blank=True)),
                ("raw_input", models.JSONField(blank=True, default=dict)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("submitted", "Submitted"), ("triaging", "AI triage in progress"), ("awaiting_review", "Awaiting human review"), ("approved", "Approved"), ("rejected", "Rejected"), ("revision_required", "Revision required"), ("remediation_in_progress", "Remediation in progress"), ("resolved", "Resolved"), ("closed", "Closed"), ("failed", "Pipeline failed"), ("reopened", "Reopened")], db_index=True, default="submitted", max_length=32)),
                ("submitted_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                ("reopened_count", models.PositiveIntegerField(default=0)),
                ("submitted_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="submitted_incidents", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("-submitted_at",)},
        ),
        migrations.CreateModel(
            name="WorkflowResult",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("current_stage", models.CharField(choices=[("not_started", "Not started"), ("normalization", "Normalization"), ("severity", "Severity"), ("root_cause", "Root cause"), ("runbook", "Runbook"), ("summary", "Summary"), ("complete", "Complete")], default="not_started", max_length=24)),
                ("normalized_data", models.JSONField(blank=True, null=True)),
                ("severity_output", models.JSONField(blank=True, null=True)),
                ("root_cause_output", models.JSONField(blank=True, null=True)),
                ("runbook_output", models.JSONField(blank=True, null=True)),
                ("summary_output", models.JSONField(blank=True, null=True)),
                ("overall_confidence", models.FloatField(blank=True, null=True)),
                ("processing_time_seconds", models.FloatField(default=0)),
                ("active_model", models.CharField(blank=True, max_length=120)),
                ("is_processing", models.BooleanField(default=False)),
                ("failure_reason", models.TextField(blank=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("incident", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="workflow", to="incidents.incident")),
            ],
        ),
        migrations.CreateModel(
            name="AgentExecution",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("stage", models.CharField(choices=[("normalization", "Normalization"), ("severity", "Severity agent"), ("root_cause", "Root-cause agent"), ("runbook", "Runbook agent"), ("summary", "Communication agent")], max_length=24)),
                ("status", models.CharField(choices=[("started", "Started"), ("success", "Success"), ("failed", "Failed")], max_length=16)),
                ("execution_mode", models.CharField(choices=[("live", "Live model"), ("mock", "Deterministic demo"), ("fallback", "Deterministic fallback")], default="live", max_length=16)),
                ("model_name", models.CharField(blank=True, max_length=120)),
                ("input_summary", models.JSONField(blank=True, default=dict)),
                ("output", models.JSONField(blank=True, default=dict)),
                ("confidence", models.FloatField(blank=True, null=True)),
                ("latency_ms", models.PositiveIntegerField(blank=True, null=True)),
                ("retry_count", models.PositiveIntegerField(default=0)),
                ("error_message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("incident", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="agent_executions", to="incidents.incident")),
            ],
            options={"ordering": ("created_at",)},
        ),
        migrations.CreateModel(
            name="ReviewDecision",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("decision", models.CharField(choices=[("approved", "Approved"), ("rejected", "Rejected"), ("revision_required", "Revision required")], max_length=24)),
                ("reviewer_note", models.TextField(blank=True)),
                ("overrides", models.JSONField(blank=True, default=dict)),
                ("decided_at", models.DateTimeField(auto_now_add=True)),
                ("incident", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reviews", to="incidents.incident")),
                ("reviewer", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("-decided_at",)},
        ),
        migrations.CreateModel(
            name="ResolutionRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("resolution_summary", models.TextField(blank=True)),
                ("confirmed_root_cause", models.TextField(blank=True)),
                ("root_cause_confirmed", models.BooleanField(default=False)),
                ("verification_notes", models.TextField(blank=True)),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                ("incident", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="resolution", to="incidents.incident")),
                ("resolved_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="resolved_incidents", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="ResolutionAction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("order", models.PositiveIntegerField(default=1)),
                ("action", models.TextField()),
                ("result", models.TextField(blank=True)),
                ("performed_by", models.CharField(blank=True, max_length=160)),
                ("performed_at", models.DateTimeField(blank=True, null=True)),
                ("resolution", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="actions", to="incidents.resolutionrecord")),
            ],
            options={"ordering": ("order", "id")},
        ),
        migrations.CreateModel(
            name="StatusEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("previous_status", models.CharField(blank=True, max_length=32)),
                ("new_status", models.CharField(max_length=32)),
                ("note", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("changed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ("incident", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="status_events", to="incidents.incident")),
            ],
            options={"ordering": ("created_at",)},
        ),
        migrations.AddIndex(model_name="incident", index=models.Index(fields=["status", "-submitted_at"], name="inc_status_submit_idx")),
        migrations.AddIndex(model_name="incident", index=models.Index(fields=["service_name", "-submitted_at"], name="inc_service_submit_idx")),
    ]
