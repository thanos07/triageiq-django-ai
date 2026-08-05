from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from .views import HealthView, RootView


admin.site.site_header = "TriageIQ Administration"
admin.site.site_title = "TriageIQ Admin"
admin.site.index_title = "Incident Operations Administration"
admin.site.site_url = settings.FRONTEND_URL


urlpatterns = [
    path("", RootView.as_view(), name="root"),

    path(
        "api/health/",
        HealthView.as_view(),
        name="health",
    ),

    path(
        "admin/",
        admin.site.urls,
    ),

    path(
        "api/auth/token/",
        TokenObtainPairView.as_view(),
        name="token_obtain_pair",
    ),

    path(
        "api/auth/refresh/",
        TokenRefreshView.as_view(),
        name="token_refresh",
    ),

    path(
        "api/auth/",
        include("accounts.urls"),
    ),

    path(
        "api/",
        include("incidents.urls"),
    ),

    path(
        "api/schema/",
        SpectacularAPIView.as_view(),
        name="schema",
    ),

    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(
            url_name="schema",
        ),
        name="swagger-ui",
    ),
]
