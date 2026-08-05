# Generated for TriageIQ temporary source-file retention.

import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("incidents", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="incident",
            name="extracted_context",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="incident",
            name="information_gaps",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.CreateModel(
            name="TemporaryIncidentFile",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("original_name", models.CharField(max_length=255)),
                ("storage_key", models.CharField(max_length=500, unique=True)),
                ("content_type", models.CharField(max_length=120)),
                ("file_type", models.CharField(choices=[("pdf", "PDF"), ("json", "JSON"), ("csv", "CSV"), ("text", "Text"), ("log", "Log")], max_length=16)),
                ("size_bytes", models.PositiveBigIntegerField()),
                ("sha256", models.CharField(db_index=True, max_length=64)),
                ("status", models.CharField(choices=[("ready", "Ready"), ("failed", "Extraction failed"), ("deleted", "Deleted")], default="ready", max_length=16)),
                ("extracted_fields", models.JSONField(blank=True, default=dict)),
                ("extracted_context", models.JSONField(blank=True, default=dict)),
                ("information_gaps", models.JSONField(blank=True, default=list)),
                ("extraction_error", models.TextField(blank=True)),
                ("retention_days", models.PositiveSmallIntegerField(default=10)),
                ("uploaded_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("expires_at", models.DateTimeField(db_index=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("incident", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="temporary_files", to="incidents.incident")),
                ("uploaded_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="temporary_incident_files", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("-uploaded_at",)},
        ),
        migrations.AddIndex(
            model_name="temporaryincidentfile",
            index=models.Index(fields=["expires_at", "status"], name="temp_file_expiry_idx"),
        ),
    ]
