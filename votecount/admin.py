from django.contrib import admin

from .models import (
    Agent,
)


# Register Agent separately if needed (optional)
@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    """
    Separate admin for Agent if needed.
    """

    list_display = ("email", "created_at", "updated_at")
    search_fields = ("user__email",)
    readonly_fields = ("created_at", "updated_at")

    def email(self, obj):
        return obj.user.email

    email.short_description = "Email"
