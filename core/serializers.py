
from django.contrib.auth.models import Group
from djoser.serializers import (
    UserCreateSerializer,
    UserSerializer,
)
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

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
                  "password",
                  'user_type'
        ]

    def create(self, validated_data):
        """
        Create a new user with a system-generated PIN.
        """
        validated_data["username"] = validated_data["email"]

        user_type = validated_data.pop('user_type', 'citizen')
        
        user = super().create(validated_data)
        
        # Adiciona ao grupo apropriado
        group, _ = Group.objects.get_or_create(name=user_type)
        user.groups.add(group)
        
        return user
    
class TokenCreateSerializer(TokenObtainPairSerializer):
    """
    Serializer for obtain token.
    """
    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = UserSerializer(self.user).data
        return data
        
    
