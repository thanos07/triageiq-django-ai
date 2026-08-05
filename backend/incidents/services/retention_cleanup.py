from __future__ import annotations

from dataclasses import dataclass

from django.utils import timezone

from incidents.models import TemporaryIncidentFile

from .temporary_storage import (
    TemporaryStorageError,
    storage,
)


@dataclass(frozen=True)
class RetentionCleanupResult:
    """Summary returned after one cleanup execution."""

    scanned: int
    deleted: int
    failed: int


def purge_expired_temporary_files(
    *,
    limit: int = 100,
) -> RetentionCleanupResult:
    """
    Physically delete expired temporary source files.

    The original object is removed from the configured storage
    provider. Extracted incident data and audit history remain
    in the database.
    """

    if limit < 1:
        raise ValueError(
            "Cleanup limit must be at least 1."
        )

    cleanup_time = timezone.now()

    expired_files = list(
        TemporaryIncidentFile.objects.filter(
            expires_at__lte=cleanup_time,
            deleted_at__isnull=True,
        )
        .exclude(
            status=(
                TemporaryIncidentFile.Status.DELETED
            )
        )
        .order_by("expires_at")[:limit]
    )

    deleted_count = 0
    failed_count = 0

    for source_file in expired_files:
        try:
            storage.delete(
                source_file.storage_key
            )
        except TemporaryStorageError:
            # Leave the database record unchanged so a later
            # cleanup execution can retry the deletion.
            failed_count += 1
            continue

        source_file.status = (
            TemporaryIncidentFile.Status.DELETED
        )
        source_file.deleted_at = cleanup_time
        source_file.save(
            update_fields=(
                "status",
                "deleted_at",
            )
        )

        deleted_count += 1

    return RetentionCleanupResult(
        scanned=len(expired_files),
        deleted=deleted_count,
        failed=failed_count,
    )