from django.apps import AppConfig


class VotecountConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "votecount"

    def ready(self):
        import votecount.signals  # noqa: F401
