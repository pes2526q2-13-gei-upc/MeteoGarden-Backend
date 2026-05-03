from django.core.management.base import BaseCommand

from api.models import Shop


class Command(BaseCommand):
    help = "Initialize default shop stock"

    def handle(self, *args, **kwargs):
        shop = Shop.get_solo()
        shop.initialize_starter_stock()

        self.stdout.write(self.style.SUCCESS("Shop stock initialized successfully"))
