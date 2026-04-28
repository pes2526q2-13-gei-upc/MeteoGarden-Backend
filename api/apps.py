from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api"

    def ready(self):
        from django.core.management import call_command

        for command in ("sync_plants", "sync_products", "sync_shop", "sync_images"):
            try:
                call_command(command)
            except Exception:
                pass

        from .firebase import initialize_firebase

        initialize_firebase()
