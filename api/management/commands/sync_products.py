from django.core.management.base import BaseCommand
from api.models import Product
from api.game_config.products import PRODUCTS


class Command(BaseCommand):
    help = "Create or update game products"

    def handle(self, *args, **kwargs):
        for p in PRODUCTS:
            Product.objects.update_or_create(
                name=p["name"],
                defaults=p
            )

        self.stdout.write(self.style.SUCCESS("Products synced successfully"))