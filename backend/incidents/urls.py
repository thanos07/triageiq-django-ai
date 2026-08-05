from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import DashboardView, IncidentViewSet, RunbookLibraryView

router = DefaultRouter()
router.register("incidents", IncidentViewSet, basename="incident")

urlpatterns = [
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("runbooks/", RunbookLibraryView.as_view(), name="runbook-library"),
    path("", include(router.urls)),
]
