from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "email", "username", "first_name", "last_name", "display_name", "role")

    def get_display_name(self, obj: User) -> str:
        return obj.get_full_name() or obj.username or obj.email
