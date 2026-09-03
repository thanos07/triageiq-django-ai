import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import User
from incidents.models import AgentExecution, AgentToolExecution, WorkflowResult


@pytest.fixture
def manager(db):
    return User.objects.create_user(
        username="investigation-manager",
        email="investigation-manager@example.com",
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
            "title": "Profile API error spike immediately after release 8.2.0",
            "description": (
                "HTTP 5xx increased immediately after deployment of release 8.2.0. "
                "The prior version is rollback compatible."
            ),
            "service_name": "profile-api",
            "environment": "production",
            "reported_severity": "high",
            "business_impact": "Customers intermittently cannot update profiles.",
        },
        format="json",
    )
    assert response.status_code == 201
    return response.json()["id"]


@pytest.mark.django_db
def test_investigation_stage_is_persisted_and_exposes_tool_audit(client, incident_id, settings):
    settings.AI_MODE = "mock"
    advance_url = reverse("incident-advance", kwargs={"pk": incident_id})

    for expected in ("normalization", "severity", "investigation"):
        response = client.post(advance_url, {}, format="json")
        assert response.status_code == 200
        assert response.json()["completed_stage"] == expected

    detail = client.get(reverse("incident-detail", kwargs={"pk": incident_id})).json()
    workflow = detail["workflow"]
    assert workflow["current_stage"] == WorkflowResult.Stage.INVESTIGATION
    assert workflow["investigation_output"]
    assert workflow["investigation_output"]["tools_used"]
    assert workflow["investigation_output"]["supporting_evidence"]

    execution = AgentExecution.objects.get(
        incident_id=incident_id,
        stage=AgentExecution.Stage.INVESTIGATION,
    )
    tool_rows = AgentToolExecution.objects.filter(agent_execution=execution).order_by("sequence")
    assert 1 <= tool_rows.count() <= 3
    assert list(tool_rows.values_list("sequence", flat=True)) == list(range(1, tool_rows.count() + 1))

    api_execution = next(item for item in detail["agent_executions"] if item["stage"] == "investigation")
    assert len(api_execution["tool_executions"]) == tool_rows.count()
    assert all(
        item["tool_name"] in {
            "get_recent_deployments",
            "get_service_metrics",
            "search_logs",
            "search_runbooks",
        }
        for item in api_execution["tool_executions"]
    )


@pytest.mark.django_db
def test_root_cause_runs_after_investigation_and_receives_evidence(client, incident_id, settings):
    settings.AI_MODE = "mock"
    advance_url = reverse("incident-advance", kwargs={"pk": incident_id})

    for _ in range(4):
        response = client.post(advance_url, {}, format="json")
        assert response.status_code == 200

    detail = client.get(reverse("incident-detail", kwargs={"pk": incident_id})).json()
    assert detail["workflow"]["investigation_output"]
    assert detail["workflow"]["root_cause_output"]
    assert detail["workflow"]["current_stage"] == WorkflowResult.Stage.ROOT_CAUSE

    evidence = " ".join(detail["workflow"]["root_cause_output"].get("evidence", [])).lower()
    assert "investigation" in evidence or "incident" in evidence
