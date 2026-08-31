from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Admin configuration for the User model.
    """

    # Display fields in the list view
    list_display = (
        "email",
        "first_name",
        "last_name",
    )

    # Fields for filtering in the sidebar
    list_filter = (
        "is_active",
        "is_staff",
        "is_superuser",
    )

    # Search fields
    search_fields = ("email", "first_name", "last_name")

    # Ordering
    ordering = ("-date_joined", "first_name")

    readonly_fields = ("date_joined",)
