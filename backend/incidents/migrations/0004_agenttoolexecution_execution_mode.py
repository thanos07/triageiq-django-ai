from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("incidents", "0003_investigation_agent_and_tool_audit"),
    ]

    operations = [
        migrations.AddField(
            model_name="agenttoolexecution",
            name="execution_mode",
            field=models.CharField(
                choices=[
                    ("live", "Live model"),
                    ("mock", "Deterministic demo"),
                    ("fallback", "Deterministic fallback"),
                ],
                default="live",
                max_length=16,
            ),
        ),
    ]
