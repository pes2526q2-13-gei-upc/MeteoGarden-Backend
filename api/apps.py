
    def ready(self):
        from django.core.management import call_command

        try:
            call_command("sync_products")
        except Exception:
            pass
