from __future__ import annotations

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from incidents.models import TemporaryIncidentFile
from incidents.services import retention_cleanup
from incidents.services.retention_cleanup import (
    purge_expired_temporary_files,
)
from incidents.services.temporary_storage import (
    TemporaryStorageError,
)


@pytest.fixture
def upload_user():
    user_model = get_user_model()

    return user_model.objects.create_user(
        username="cleanup-test-user",
        email="cleanup-test@example.com",
        password="CleanupTestPass123!",
    )


def create_temporary_file(
    *,
    upload_user,
    storage_key: str,
    expires_at,
) -> TemporaryIncidentFile:
    return TemporaryIncidentFile.objects.create(
        uploaded_by=upload_user,
        original_name="test-source.txt",
        storage_key=storage_key,
        content_type="text/plain",
        file_type=TemporaryIncidentFile.FileType.TEXT,
        size_bytes=54,
        sha256="a" * 64,
        retention_days=7,
        expires_at=expires_at,
    )


@pytest.mark.django_db
def test_cleanup_deletes_expired_file_and_updates_record(
    upload_user,
    monkeypatch,
):
    source_file = create_temporary_file(
        upload_user=upload_user,
        storage_key=(
            "temporary-incidents/7-days/"
            "expired-source.txt"
        ),
        expires_at=(
            timezone.now()
            - timedelta(minutes=5)
        ),
    )

    deleted_keys: list[str] = []

    def fake_delete(key: str) -> None:
        deleted_keys.append(key)

    monkeypatch.setattr(
        retention_cleanup.storage,
        "delete",
        fake_delete,
    )

    result = purge_expired_temporary_files(
        limit=10,
    )

    source_file.refresh_from_db()

    assert result.scanned == 1
    assert result.deleted == 1
    assert result.failed == 0

    assert deleted_keys == [
        source_file.storage_key
    ]

    assert (
        source_file.status
        == TemporaryIncidentFile.Status.DELETED
    )
    assert source_file.deleted_at is not None


@pytest.mark.django_db
def test_cleanup_does_not_delete_unexpired_file(
    upload_user,
    monkeypatch,
):
    source_file = create_temporary_file(
        upload_user=upload_user,
        storage_key=(
            "temporary-incidents/7-days/"
            "future-source.txt"
        ),
        expires_at=(
            timezone.now()
            + timedelta(days=1)
        ),
    )

    deleted_keys: list[str] = []

    def fake_delete(key: str) -> None:
        deleted_keys.append(key)

    monkeypatch.setattr(
        retention_cleanup.storage,
        "delete",
        fake_delete,
    )

    result = purge_expired_temporary_files(
        limit=10,
    )

    source_file.refresh_from_db()

    assert result.scanned == 0
    assert result.deleted == 0
    assert result.failed == 0

    assert deleted_keys == []
    assert (
        source_file.status
        == TemporaryIncidentFile.Status.READY
    )
    assert source_file.deleted_at is None


@pytest.mark.django_db
def test_cleanup_retries_after_storage_failure(
    upload_user,
    monkeypatch,
):
    source_file = create_temporary_file(
        upload_user=upload_user,
        storage_key=(
            "temporary-incidents/7-days/"
            "retry-source.txt"
        ),
        expires_at=(
            timezone.now()
            - timedelta(minutes=5)
        ),
    )

    def failing_delete(key: str) -> None:
        raise TemporaryStorageError(
            f"Could not delete {key}"
        )

    monkeypatch.setattr(
        retention_cleanup.storage,
        "delete",
        failing_delete,
    )

    result = purge_expired_temporary_files(
        limit=10,
    )

    source_file.refresh_from_db()

    assert result.scanned == 1
    assert result.deleted == 0
    assert result.failed == 1

    assert (
        source_file.status
        == TemporaryIncidentFile.Status.READY
    )
    assert source_file.deleted_at is None