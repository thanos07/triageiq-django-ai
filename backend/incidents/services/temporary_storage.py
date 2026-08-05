from __future__ import annotations

from pathlib import Path
from typing import BinaryIO

import boto3
from botocore.config import Config
from django.conf import settings


class TemporaryStorageError(RuntimeError):
    """Raised when a temporary source document cannot be stored or retrieved."""


class TemporaryObjectStorage:
    """Private temporary storage with S3-compatible and local modes."""

    @property
    def mode(self) -> str:
        return settings.TEMP_UPLOAD_STORAGE_MODE

    @property
    def uses_object_storage(self) -> bool:
        return self.mode in {"s3", "r2"}

    def _s3_client(self):
        required = {
            "S3_ENDPOINT_URL": settings.S3_ENDPOINT_URL,
            "S3_ACCESS_KEY_ID": settings.S3_ACCESS_KEY_ID,
            "S3_SECRET_ACCESS_KEY": settings.S3_SECRET_ACCESS_KEY,
            "S3_BUCKET_NAME": settings.S3_BUCKET_NAME,
            "S3_REGION": settings.S3_REGION,
        }

        missing = [
            name
            for name, value in required.items()
            if not value
        ]

        if missing:
            raise TemporaryStorageError(
                "S3-compatible storage is selected but these settings "
                "are missing: "
                + ", ".join(missing)
            )

        addressing_style = (
            "path"
            if settings.S3_FORCE_PATH_STYLE
            else "auto"
        )

        return boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
            region_name=settings.S3_REGION,
            config=Config(
                signature_version="s3v4",
                retries={
                    "max_attempts": 3,
                    "mode": "standard",
                },
                s3={
                    "addressing_style": addressing_style,
                },
            ),
        )

    def put(
        self,
        *,
        key: str,
        payload: bytes,
        content_type: str,
        metadata: dict[str, str] | None = None,
    ) -> None:
        if self.uses_object_storage:
            try:
                self._s3_client().put_object(
                    Bucket=settings.S3_BUCKET_NAME,
                    Key=key,
                    Body=payload,
                    ContentType=(
                        content_type
                        or "application/octet-stream"
                    ),
                    Metadata=metadata or {},
                )
            except Exception as exc:
                raise TemporaryStorageError(
                    "Could not upload the temporary source file: "
                    f"{exc}"
                ) from exc

            return

        path = self._local_path(key)
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        path.write_bytes(payload)

    def get(self, key: str) -> bytes:
        if self.uses_object_storage:
            try:
                response = self._s3_client().get_object(
                    Bucket=settings.S3_BUCKET_NAME,
                    Key=key,
                )
                body: BinaryIO = response["Body"]
                return body.read()
            except Exception as exc:
                raise TemporaryStorageError(
                    "Could not read the temporary source file: "
                    f"{exc}"
                ) from exc

        path = self._local_path(key)

        if not path.exists():
            raise TemporaryStorageError(
                "The temporary source file no longer exists."
            )

        return path.read_bytes()

    def delete(self, key: str) -> None:
        if self.uses_object_storage:
            try:
                self._s3_client().delete_object(
                    Bucket=settings.S3_BUCKET_NAME,
                    Key=key,
                )
            except Exception as exc:
                raise TemporaryStorageError(
                    "Could not delete the temporary source file: "
                    f"{exc}"
                ) from exc

            return

        path = self._local_path(key)

        try:
            path.unlink(missing_ok=True)
        except OSError as exc:
            raise TemporaryStorageError(
                "Could not delete the local temporary source file: "
                f"{exc}"
            ) from exc

    def _local_path(self, key: str) -> Path:
        root = Path(
            settings.TEMP_UPLOAD_LOCAL_ROOT
        ).resolve()

        candidate = (root / key).resolve()

        if (
            root not in candidate.parents
            and candidate != root
        ):
            raise TemporaryStorageError(
                "Unsafe temporary storage key."
            )

        return candidate


storage = TemporaryObjectStorage()