import pytest

from core.models import User


@pytest.fixture
def user_valid_data():
    return {
        "first_name": "John",
        "last_name": "Smith",
        "email": "user@website.com",
        "username": "user@website.com",
        "password": "password123",
    }


@pytest.mark.django_db
class TestCoreModels:
    def test_create_new_user(self, user_valid_data):

        # Given
        data = user_valid_data

        # Act
        saved_user = User.objects.create(**data)
        users_count = len(User.objects.all())

        # Then
        assert users_count == 1
        assert saved_user.username == data["email"]

    def test_create_agent_when_user_is_created(self, user_valid_data):
        # Given
        data = user_valid_data

        # Act
        saved_user = User.objects.create(**data)
        users_count = len(User.objects.all())
        
        # Then
        assert users_count == 1
        assert saved_user.agent.id == 1
