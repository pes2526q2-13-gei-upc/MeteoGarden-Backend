from django.apps import AppConfig
from django.conf import settings


class ApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api"

    def ready(self):
        from .firebase import initialize_firebase

        if not getattr(settings, "FIREBASE_ENABLED", False):
            return
        initialize_firebase()
