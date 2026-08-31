
from djoser.serializers import (
    UserCreateSerializer,
    UserSerializer,
)

from .models import User


class UserSerializer(UserSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "username",
        ]


class UserCreateSerializer(UserCreateSerializer):
    """
    Serializer for user registration.
    """

    class Meta:
        model = User
        fields = [
                  "id", 
                  "first_name",
                  "last_name",
                  "email",
                  "username",
                  "password"
        ]

    def create(self, validated_data):
        """
        Create a new user with a system-generated PIN.
        """
        validated_data["username"] = validated_data["email"]
        return super().create(validated_data)
