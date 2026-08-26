from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("incidents", "0002_temporaryincidentfile_and_extraction_fields"),
    ]

    operations = [
        migrations.AlterField(
            model_name="workflowresult",
            name="current_stage",
            field=models.CharField(
                choices=[
                    ("not_started", "Not started"),
                    ("normalization", "Normalization"),
                    ("severity", "Severity"),
                    ("investigation", "Investigation"),
                    ("root_cause", "Root cause"),
                    ("runbook", "Runbook"),
                    ("summary", "Summary"),
                    ("complete", "Complete"),
                ],
                default="not_started",
                max_length=24,
            ),
        ),
        migrations.AddField(
            model_name="workflowresult",
            name="investigation_output",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="agentexecution",
            name="stage",
            field=models.CharField(
                choices=[
                    ("normalization", "Normalization"),
                    ("severity", "Severity agent"),
                    ("investigation", "Investigation agent"),
                    ("root_cause", "Root-cause agent"),
                    ("runbook", "Runbook agent"),
                    ("summary", "Communication agent"),
                ],
                max_length=24,
            ),
        ),
        migrations.CreateModel(
            name="AgentToolExecution",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sequence", models.PositiveSmallIntegerField(default=1)),
                ("tool_name", models.CharField(max_length=80)),
                ("arguments", models.JSONField(blank=True, default=dict)),
                ("result", models.JSONField(blank=True, default=dict)),
                ("status", models.CharField(choices=[("started", "Started"), ("success", "Success"), ("failed", "Failed")], max_length=16)),
                ("latency_ms", models.PositiveIntegerField(blank=True, null=True)),
                ("error_message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("agent_execution", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="tool_executions", to="incidents.agentexecution")),
                ("incident", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="tool_executions", to="incidents.incident")),
            ],
            options={
                "ordering": ("agent_execution_id", "sequence", "id"),
                "constraints": [
                    models.UniqueConstraint(fields=("agent_execution", "sequence"), name="uniq_agent_tool_sequence"),
                ],
            },
        ),
    ]
