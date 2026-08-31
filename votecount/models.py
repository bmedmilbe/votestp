
from django.conf import settings
from django.db import models


class Agent(models.Model):
    """
    Customer profile model that links to the user model via OneToOneField.
    This is the ONLY model that directly links to the user model.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="agent"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Agent {self.user.first_name} {self.user.last_name}"

    
