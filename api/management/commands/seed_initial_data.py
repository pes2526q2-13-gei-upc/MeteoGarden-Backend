from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Seed all initial data: plants, images, products and shop"

    def handle(self, *args, **options):
        self.stdout.write("Seeding plants...")
        call_command("sync_plants")

        self.stdout.write("Seeding images...")
        call_command("sync_images")

        self.stdout.write("Seeding products...")
        call_command("sync_products")

        self.stdout.write("Seeding shop...")
        call_command("sync_shop")

        self.stdout.write("Seeding missions...")
        call_command("sync_missions")

        self.stdout.write(self.style.SUCCESS("All initial data seeded successfully."))
