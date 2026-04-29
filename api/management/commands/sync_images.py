from django.core.management.base import BaseCommand

from api.game_config.images import STARTER_IMAGES
from api.models import Image, Plant


class Command(BaseCommand):
    help = "Create or update starter plant images"

    def handle(self, *args, **kwargs):
        for entry in STARTER_IMAGES:
            try:
                plant = Plant.objects.get(scientificName=entry["plant"])
                Image.objects.get_or_create(
                    plant=plant,
                    growthPhase=entry["phase"],
                    defaults={"url": entry["url"]},
                )
            except Plant.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f"Plant {entry['plant']} not found, skipping.")
                )

        self.stdout.write(self.style.SUCCESS("Images synced successfully"))