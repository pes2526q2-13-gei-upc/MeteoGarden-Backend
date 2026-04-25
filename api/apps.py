from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api"

    def ready(self):
        from django.core.management import call_command

        try:
            call_command("sync_products")
        except Exception:
            pass
