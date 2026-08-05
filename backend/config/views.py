from __future__ import annotations

import secrets

from django.conf import settings
from django.db import connection
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from incidents.services.retention_cleanup import (
    purge_expired_temporary_files,
)


class RootView(APIView):
    """
    Public information endpoint for the TriageIQ backend root URL.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response(
            {
                "service": "TriageIQ API",
                "status": "online",
                "frontend": settings.FRONTEND_URL,
                "health": request.build_absolute_uri(
                    "/api/health/"
                ),
                "documentation": request.build_absolute_uri(
                    "/api/docs/"
                ),
                "admin": request.build_absolute_uri(
                    "/admin/"
                ),
            }
        )


class HealthView(APIView):
    """
    Public health-check endpoint for the API and database.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        database_status = "ok"

        try:
            connection.ensure_connection()
        except Exception:
            database_status = "unavailable"

        response_status = (
            "ok"
            if database_status == "ok"
            else "degraded"
        )

        http_status_code = (
            200
            if database_status == "ok"
            else 503
        )

        return Response(
            {
                "service": "triageiq-api",
                "status": response_status,
                "database": database_status,
            },
            status=http_status_code,
        )


class RetentionCleanupView(APIView):
    """
    Secure endpoint invoked by Vercel Cron to remove
    expired temporary source files.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        configured_secret = settings.CRON_SECRET

        authorization_header = request.headers.get(
            "Authorization",
            "",
        )

        expected_header = (
            f"Bearer {configured_secret}"
        )

        if (
            not configured_secret
            or not secrets.compare_digest(
                authorization_header,
                expected_header,
            )
        ):
            return Response(
                {
                    "detail": "Unauthorized."
                },
                status=(
                    status.HTTP_401_UNAUTHORIZED
                ),
            )

        result = purge_expired_temporary_files(
            limit=(
                settings
                .TEMP_UPLOAD_CLEANUP_BATCH_SIZE
            )
        )

        return Response(
            {
                "status": "ok",
                "scanned": result.scanned,
                "deleted": result.deleted,
                "failed": result.failed,
            }
        )