from django.core.management.base import BaseCommand

from api.game_config.plants import STARTER_PLANTS
from api.models import Plant


class Command(BaseCommand):
    help = "Create or update starter plants in the database"

    def handle(self, *args, **kwargs):
        for p in STARTER_PLANTS:
            Plant.objects.update_or_create(
                scientificName=p["scientificName"],
                defaults=p,
            )

        self.stdout.write(self.style.SUCCESS("Plants synced successfully"))