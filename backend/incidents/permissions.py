from rest_framework.permissions import BasePermission

from accounts.models import User


class IsIncidentManager(BasePermission):
    message = "Only administrators and incident managers can perform this action."

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in {
            User.Role.ADMIN,
            User.Role.INCIDENT_MANAGER,
        }


class IsReviewer(BasePermission):
    message = "Only administrators and reviewers can perform this action."

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in {
            User.Role.ADMIN,
            User.Role.REVIEWER,
        }
