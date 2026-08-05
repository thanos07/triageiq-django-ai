from django.conf import settings
from django.db import connection
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


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
                "health": request.build_absolute_uri("/api/health/"),
                "documentation": request.build_absolute_uri("/api/docs/"),
                "admin": request.build_absolute_uri("/admin/"),
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