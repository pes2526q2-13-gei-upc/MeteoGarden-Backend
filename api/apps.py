
    def ready(self):
        from django.core.management import call_command

        for command in ("sync_plants", "sync_products", "sync_shop", "sync_images"):
            try:
                call_command(command)
            except Exception:
                pass
