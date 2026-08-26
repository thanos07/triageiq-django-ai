import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import User
from ai_engine.agents.investigation import InvestigationToolRun
from incidents.models import AgentExecution, AgentToolExecution


@pytest.fixture
def manager(db):
    return User.objects.create_user(
        username="audit-manager",
        email="audit-manager@example.com",
        password="StrongPass123!",
        role=User.Role.ADMIN,
    )


@pytest.fixture
def client(manager):
    api = APIClient()
    api.force_authenticate(manager)
    return api


@pytest.fixture
def incident_id(client):
    response = client.post(
        reverse("incident-list"),
        {
            "title": "Profile API errors after release",
            "description": "HTTP 5xx increased immediately after release 8.2.0.",
            "service_name": "profile-api",
            "environment": "production",
            "reported_severity": "high",
            "business_impact": "Profile updates fail.",
        },
        format="json",
    )
    assert response.status_code == 201
    return response.json()["id"]


@pytest.mark.django_db
def test_partial_tool_trace_survives_unexpected_agent_failure(
    client, incident_id, settings, monkeypatch
):
    settings.AI_MODE = "mock"
    advance_url = reverse("incident-advance", kwargs={"pk": incident_id})

    for _ in range(2):
        response = client.post(advance_url, {}, format="json")
        assert response.status_code == 200

    def fail_after_first_tool(self, context, *, on_tool_execution=None):
        assert on_tool_execution is not None
        on_tool_execution(
            InvestigationToolRun(
                sequence=1,
                tool_name="get_service_metrics",
                arguments={"service_name": "profile-api"},
                result={"service_name": "profile-api", "found": True, "window": "last_15m", "values": []},
                status="success",
                latency_ms=2,
                execution_mode="mock",
            )
        )
        raise RuntimeError("synthetic crash after first tool")

    monkeypatch.setattr("ai_engine.pipeline.InvestigationAgent.run", fail_after_first_tool)

    with pytest.raises(RuntimeError, match="synthetic crash"):
        client.post(advance_url, {}, format="json")

    execution = AgentExecution.objects.get(
        incident_id=incident_id,
        stage=AgentExecution.Stage.INVESTIGATION,
    )
    assert execution.status == AgentExecution.Status.FAILED

    rows = list(AgentToolExecution.objects.filter(agent_execution=execution).order_by("sequence"))
    assert len(rows) == 1
    assert rows[0].tool_name == "get_service_metrics"
    assert rows[0].status == AgentToolExecution.Status.SUCCESS
    assert rows[0].execution_mode == AgentExecution.Mode.MOCK


@pytest.mark.django_db
def test_mock_tool_rows_record_mode(client, incident_id, settings):
    settings.AI_MODE = "mock"
    advance_url = reverse("incident-advance", kwargs={"pk": incident_id})

    for _ in range(3):
        response = client.post(advance_url, {}, format="json")
        assert response.status_code == 200

    execution = AgentExecution.objects.get(
        incident_id=incident_id,
        stage=AgentExecution.Stage.INVESTIGATION,
    )
    rows = AgentToolExecution.objects.filter(agent_execution=execution)
    assert rows.exists()
    assert set(rows.values_list("execution_mode", flat=True)) == {AgentExecution.Mode.MOCK}
