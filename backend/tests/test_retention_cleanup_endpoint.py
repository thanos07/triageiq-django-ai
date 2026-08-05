from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from incidents.services.retention_cleanup import (
    RetentionCleanupResult,
)


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.mark.django_db
def test_cleanup_endpoint_rejects_missing_secret(
    api_client,
    settings,
):
    settings.CRON_SECRET = "test-cron-secret"

    response = api_client.get(
        "/api/cron/purge-expired-uploads/"
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Unauthorized."
    }


@pytest.mark.django_db
def test_cleanup_endpoint_rejects_wrong_secret(
    api_client,
    settings,
):
    settings.CRON_SECRET = "test-cron-secret"

    response = api_client.get(
        "/api/cron/purge-expired-uploads/",
        HTTP_AUTHORIZATION="Bearer wrong-secret",
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Unauthorized."
    }


@pytest.mark.django_db
def test_cleanup_endpoint_runs_with_valid_secret(
    api_client,
    settings,
    monkeypatch,
):
    settings.CRON_SECRET = "test-cron-secret"
    settings.TEMP_UPLOAD_CLEANUP_BATCH_SIZE = 100

    received_limits: list[int] = []

    def fake_cleanup(
        *,
        limit: int,
    ) -> RetentionCleanupResult:
        received_limits.append(limit)

        return RetentionCleanupResult(
            scanned=3,
            deleted=2,
            failed=1,
        )

    monkeypatch.setattr(
        "config.views."
        "purge_expired_temporary_files",
        fake_cleanup,
    )

    response = api_client.get(
        "/api/cron/purge-expired-uploads/",
        HTTP_AUTHORIZATION=(
            "Bearer test-cron-secret"
        ),
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "scanned": 3,
        "deleted": 2,
        "failed": 1,
    }

    assert received_limits == [100]