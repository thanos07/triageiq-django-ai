from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Administrator"
        INCIDENT_MANAGER = "incident_manager", "Incident Manager"
        REVIEWER = "reviewer", "Reviewer"
        VIEWER = "viewer", "Viewer"

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=32, choices=Role.choices, default=Role.VIEWER)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self) -> str:
        return self.get_full_name() or self.email
