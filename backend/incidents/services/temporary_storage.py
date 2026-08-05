from __future__ import annotations

import os
from pathlib import Path
from typing import BinaryIO

import boto3
from botocore.config import Config
from django.conf import settings


class TemporaryStorageError(RuntimeError):
    """Raised when a temporary source document cannot be stored or retrieved."""


class TemporaryObjectStorage:
    """Private temporary object storage with R2 and local-development modes."""

    @property
    def mode(self) -> str:
        return settings.TEMP_UPLOAD_STORAGE_MODE

    def _r2_client(self):
        required = {
            "R2_ENDPOINT_URL": settings.R2_ENDPOINT_URL,
            "R2_ACCESS_KEY_ID": settings.R2_ACCESS_KEY_ID,
            "R2_SECRET_ACCESS_KEY": settings.R2_SECRET_ACCESS_KEY,
            "R2_BUCKET_NAME": settings.R2_BUCKET_NAME,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise TemporaryStorageError(
                "R2 storage is selected but these settings are missing: " + ", ".join(missing)
            )
        return boto3.client(
            "s3",
            endpoint_url=settings.R2_ENDPOINT_URL,
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            region_name="auto",
            config=Config(signature_version="s3v4", retries={"max_attempts": 3, "mode": "standard"}),
        )

    def put(self, *, key: str, payload: bytes, content_type: str, metadata: dict[str, str] | None = None) -> None:
        if self.mode == "r2":
            try:
                self._r2_client().put_object(
                    Bucket=settings.R2_BUCKET_NAME,
                    Key=key,
                    Body=payload,
                    ContentType=content_type or "application/octet-stream",
                    Metadata=metadata or {},
                )
            except Exception as exc:  # pragma: no cover - depends on external R2
                raise TemporaryStorageError(f"Could not upload the temporary source file: {exc}") from exc
            return

        path = self._local_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)

    def get(self, key: str) -> bytes:
        if self.mode == "r2":
            try:
                response = self._r2_client().get_object(Bucket=settings.R2_BUCKET_NAME, Key=key)
                body: BinaryIO = response["Body"]
                return body.read()
            except Exception as exc:  # pragma: no cover - depends on external R2
                raise TemporaryStorageError(f"Could not read the temporary source file: {exc}") from exc

        path = self._local_path(key)
        if not path.exists():
            raise TemporaryStorageError("The temporary source file no longer exists.")
        return path.read_bytes()

    def delete(self, key: str) -> None:
        if self.mode == "r2":
            try:
                self._r2_client().delete_object(Bucket=settings.R2_BUCKET_NAME, Key=key)
            except Exception as exc:  # pragma: no cover - depends on external R2
                raise TemporaryStorageError(f"Could not delete the temporary source file: {exc}") from exc
            return

        path = self._local_path(key)
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:
            raise TemporaryStorageError(f"Could not delete the local temporary source file: {exc}") from exc

    def _local_path(self, key: str) -> Path:
        root = Path(settings.TEMP_UPLOAD_LOCAL_ROOT).resolve()
        candidate = (root / key).resolve()
        if root not in candidate.parents and candidate != root:
            raise TemporaryStorageError("Unsafe temporary storage key.")
        return candidate


storage = TemporaryObjectStorage()
