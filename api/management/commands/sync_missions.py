from django.core.management.base import BaseCommand

from api.game_config.missions import MISSIONS
from api.models import Mission, Plant, Product


class Command(BaseCommand):
    help = "Create or update game missions"

    def handle(self, *args, **kwargs):
        for data in MISSIONS:
            data = data.copy()

            plant_name = data.pop("plant")
            product_name = data.pop("product")
            plant_reward_name = data.pop("plantReward")
            product_reward_name = data.pop("productReward")

            plant = (
                Plant.objects.filter(scientificName=plant_name).first()
                if plant_name
                else None
            )
            product = (
                Product.objects.filter(name=product_name).first()
                if product_name
                else None
            )
            plant_reward = (
                Plant.objects.filter(scientificName=plant_reward_name).first()
                if plant_reward_name
                else None
            )
            product_reward = (
                Product.objects.filter(name=product_reward_name).first()
                if product_reward_name
                else None
            )

            mission, created = Mission.objects.update_or_create(
                name=data["name"],
                defaults={
                    **data,
                    "plant": plant,
                    "product": product,
                    "plantReward": plant_reward,
                    "productReward": product_reward,
                },
            )

            self.stdout.write(
                f"{'Created' if created else 'Updated'} mission: {mission.name}"
            )

        self.stdout.write(self.style.SUCCESS("Missions synced successfully"))
