from django.contrib import admin

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


class AgentExecutionInline(admin.TabularInline):
    model = AgentExecution
    extra = 0
    readonly_fields = ("stage", "status", "execution_mode", "model_name", "confidence", "latency_ms", "created_at")


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = ("reference", "title", "service_name", "environment", "status", "submitted_at")
    list_filter = ("status", "environment", "reported_severity")
    search_fields = ("title", "description", "service_name")
    readonly_fields = ("id", "submitted_at", "updated_at", "resolved_at")
    inlines = (AgentExecutionInline,)


admin.site.register(WorkflowResult)
admin.site.register(AgentExecution)
admin.site.register(ReviewDecision)
admin.site.register(ResolutionRecord)
admin.site.register(ResolutionAction)
admin.site.register(StatusEvent)

admin.site.register(TemporaryIncidentFile)
