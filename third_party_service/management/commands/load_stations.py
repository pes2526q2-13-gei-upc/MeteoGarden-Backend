import requests
from django.core.management.base import BaseCommand

from api.models import Station


class Command(BaseCommand):
    help = "Carrega les estacions del XEMA a la BD"

    def handle(self, *args, **kwargs):
        url = (
            "https://analisi.transparenciacatalunya.cat/resource/yqwd-vj5e.json"
            "?$select=nom_estacio,codi_estacio,nom_municipi"
            "&$where=nom_estat_ema='Operativa'"
            "&$order=nom_estacio"
        )
        rows = requests.get(url, timeout=10).json()

        created = 0
        for row in rows:
            _, was_created = Station.objects.get_or_create(
                stationCode=row.get("codi_estacio"),
                defaults={
                    "station": row.get("nom_estacio", ""),
                    "city": row.get("nom_estacio", ""),
                    "solarIrradiance": 0,
                    "temperature": 0.0,
                    "precipitation": 0.0,
                    "windSpeed": 0.0,
                    "relativeHumidity": 0.0,
                },
            )
            if was_created:
                created += 1

        self.stdout.write(f"{created} estacions carregades.")
