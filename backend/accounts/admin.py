from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class TriageIQUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("TriageIQ", {"fields": ("role",)}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("TriageIQ", {"fields": ("email", "role")}),)
    list_display = ("email", "username", "role", "is_staff", "is_active")
    list_filter = ("role", "is_staff", "is_active")
