from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import (
    Agent,
)


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def save_agent_for_user(sender, instance, **kwargs):
    """Save the Agent when User is saved."""
    try:
        instance.agent.save()
    except Agent.DoesNotExist:
        Agent.objects.create(user=instance)
