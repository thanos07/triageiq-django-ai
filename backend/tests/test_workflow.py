import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import User
from incidents.models import Incident


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="operator",
        email="operator@example.com",
        password="StrongPass123!",
        role=User.Role.ADMIN,
    )


@pytest.fixture
def client(user):
    api = APIClient()
    api.force_authenticate(user)
    return api


@pytest.fixture
def incident(client):
    response = client.post(
        reverse("incident-list"),
        {
            "title": "Production checkout returns 502 after deployment",
            "description": "Checkout requests fail after release 8.2. Production gateway logs contain 502 errors.",
            "service_name": "checkout-api",
            "environment": "production",
            "reported_severity": "high",
            "business_impact": "Customers cannot complete some purchases.",
        },
        format="json",
    )
    assert response.status_code == 201
    return response.json()


@pytest.mark.django_db
def test_full_incident_lifecycle_and_pdf(client, incident):
    incident_id = incident["id"]
    advance_url = reverse("incident-advance", kwargs={"pk": incident_id})

    for _ in range(5):
        response = client.post(advance_url, {}, format="json")
        assert response.status_code == 200

    detail = client.get(reverse("incident-detail", kwargs={"pk": incident_id})).json()
    assert detail["status"] == Incident.Status.AWAITING_REVIEW
    assert detail["workflow"]["current_stage"] == "complete"
    assert detail["workflow"]["severity_output"]["level"] in {"critical", "high", "medium", "low"}

    response = client.post(
        reverse("incident-review", kwargs={"pk": incident_id}),
        {"decision": "approved", "reviewer_note": "Telemetry supports the response plan."},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["status"] == "approved"

    response = client.post(reverse("incident-start-resolution", kwargs={"pk": incident_id}), {}, format="json")
    assert response.status_code == 200
    assert response.json()["status"] == "remediation_in_progress"

    response = client.post(
        reverse("incident-resolve", kwargs={"pk": incident_id}),
        {
            "resolution_summary": "Rollback restored checkout traffic.",
            "confirmed_root_cause": "Deployment regression in release 8.2.",
            "root_cause_confirmed": True,
            "verification_notes": "Error rate and checkout success stayed normal for ten minutes.",
            "actions": [
                {
                    "order": 1,
                    "action": "Rolled back release 8.2.",
                    "result": "502 errors stopped.",
                    "performed_by": "On-call engineer"
                }
            ],
        },
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["status"] == "resolved"

    response = client.get(reverse("incident-report", kwargs={"pk": incident_id}))
    assert response.status_code == 200
    payload = b"".join(response.streaming_content)
    assert payload.startswith(b"%PDF")


@pytest.mark.django_db
def test_unauthenticated_request_is_rejected():
    response = APIClient().get(reverse("incident-list"))
    assert response.status_code == 401


@pytest.mark.django_db
def test_temporary_json_upload_links_to_incident_and_feeds_runbook(client, tmp_path, settings):
    import json
    from django.core.files.uploadedfile import SimpleUploadedFile
    from incidents.models import TemporaryIncidentFile

    settings.TEMP_UPLOAD_STORAGE_MODE = "local"
    settings.TEMP_UPLOAD_LOCAL_ROOT = str(tmp_path / "temporary-uploads")

    source_payload = {
        "title": "Inventory API returning timeout errors",
        "description": "Requests started timing out after a deployment. No metrics were attached.",
        "service": "inventory-api",
    }
    uploaded = SimpleUploadedFile(
        "incident.json",
        json.dumps(source_payload).encode("utf-8"),
        content_type="application/json",
    )
    extraction = client.post(
        reverse("incident-extract-upload"),
        {"file": uploaded, "retention_days": "7"},
        format="multipart",
    )
    assert extraction.status_code == 201
    extraction_data = extraction.json()
    assert extraction_data["source_file"]["retention_days"] == 7
    assert extraction_data["fields"]["service_name"] == "inventory-api"
    assert any(gap["field"] == "business_impact" for gap in extraction_data["information_gaps"])

    create_response = client.post(
        reverse("incident-list"),
        {
            "title": extraction_data["fields"]["title"],
            "description": extraction_data["fields"]["description"],
            "service_name": extraction_data["fields"]["service_name"],
            "environment": "other",
            "reported_severity": "unknown",
            "business_impact": "",
            "source_file_id": extraction_data["source_file"]["id"],
            "extracted_context": extraction_data["extracted_context"],
            "information_gaps": extraction_data["information_gaps"],
        },
        format="json",
    )
    assert create_response.status_code == 201
    incident_id = create_response.json()["id"]
    source_file = TemporaryIncidentFile.objects.get(id=extraction_data["source_file"]["id"])
    assert str(source_file.incident_id) == incident_id

    for _ in range(5):
        result = client.post(reverse("incident-advance", kwargs={"pk": incident_id}), {}, format="json")
        assert result.status_code == 200

    detail = client.get(reverse("incident-detail", kwargs={"pk": incident_id})).json()
    runbook_gaps = detail["workflow"]["runbook_output"]["missing_information"]
    assert any(item["field"] == "business_impact" for item in runbook_gaps)
    assert detail["source_file"]["availability"] == "ready"

    delete_response = client.post(
        reverse("incident-delete-source-file", kwargs={"pk": incident_id}),
        {},
        format="json",
    )
    assert delete_response.status_code == 200
    assert delete_response.json()["availability"] == "deleted"
    assert not (tmp_path / "temporary-uploads" / source_file.storage_key).exists()


@pytest.mark.django_db
def test_runbook_library_api_exposes_30_problem_solution_cases(client):
    response = client.get(reverse("runbook-library"))
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 30
    assert payload["count"] == 30
    assert len(payload["results"]) == 30
    first = payload["results"][0]
    assert first["problem"]
    assert first["diagnostic_steps"]
    assert first["solution_steps"]
    assert first["verification_steps"]
