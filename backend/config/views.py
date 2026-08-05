from django.db import connection
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        database = "ok"
        try:
            connection.ensure_connection()
        except Exception:
            database = "unavailable"
        status_code = 200 if database == "ok" else 503
        return Response({"service": "triageiq-api", "status": "ok" if status_code == 200 else "degraded", "database": database}, status=status_code)
