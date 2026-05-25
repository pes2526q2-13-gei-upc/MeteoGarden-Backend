from django.core.management.base import BaseCommand

# Importa la funció des d'on la tinguis guardada actualment (canvia 'el_teu_modul')
from api.tasks import sync_events_task


class Command(BaseCommand):
    help = "Sincronitza els esdeveniments des del servei extern"

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.WARNING("Iniciant la sincronització d'esdeveniments...")
        )

        resultat = sync_events_task()

        self.stdout.write(self.style.SUCCESS(resultat))
