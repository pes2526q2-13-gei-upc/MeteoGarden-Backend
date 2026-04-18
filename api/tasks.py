from celery import shared_task
from django.utils import timezone

from api.models import Garden, GrowthState, Station
from api.plant_simulation import simulate_plant
from api.xema_sync import ensure_station_synced
from api.notifications import send_push_notification, can_send_notification


@shared_task
def simulate_all_plants():
    gardens = Garden.objects.select_related("user").all()

    for garden in gardens:
        user = garden.user

        station = Station.objects.filter(
            stationCode=user.stationCode
        ).first()

        if not station:
            continue

        # Actualitzar dades meteo
        ensure_station_synced(station)

        # Agafa totes les plantes vives
        pots = (
            garden.pot_set
            .exclude(plantingarden__isnull=True)
            .exclude(plantingarden__growthPhase=GrowthState.DEAD)
            .select_related("plantingarden__plant")
        )

        # Simula cada planta
        for pot in pots:
            pig = pot.plantingarden
            old_phase = pig.growthPhase
            old_health = pig.healthLevel

            updated = simulate_plant(pig, station)
            updated.save()

            # Notificacions
            if not can_send_notification(updated):
                continue

            # Planta baixa de salut
            if updated.healthLevel < 20:
                send_push_notification(
                    user,
                    "⚠️ Planta en perill",
                    f"{updated.plant.commonName} està molt malament"
                )
                updated.lastNotificationAt = timezone.now()
                updated.save()
                continue
            #terminal
            if pig.healthLevel < 20 and old_health >= 20:
                print(f"NOTIFICACIÓ: {user.username}, la teva planta {pig.plant.commonName} està molt malalta!")

            # Planta morta
            if updated.growthPhase == GrowthState.DEAD:
                send_push_notification(
                    user,
                    "💀 Planta morta",
                    f"La teva planta {updated.plant.commonName} ha mort"
                )
                updated.lastNotificationAt = timezone.now()
                updated.save()
                continue

            if pig.growthPhase == GrowthState.DEAD and old_phase != GrowthState.DEAD:
                print(f"NOTIFICACIÓ: {user.username}, la teva planta {pig.plant.commonName} ha mort.")

            # Planta canvia de fase
            if pig.growthPhase != old_phase:
                print(f"NOTIFICACIÓ: {user.username}, la planta {pig.plant.commonName} ha passat a fase {pig.growthPhase}!")

            # 📉 caiguda brusca salut
            if old_health - updated.healthLevel > 15:
                send_push_notification(
                    user,
                    "📉 Canvi brusc",
                    f"{updated.plant.commonName} ha empitjorat ràpidament"
                )
                updated.lastNotificationAt = timezone.now()
                updated.save()

#7. docker-compose.yml — afegir redis, celery-worker i celery-beat (ja te'l vaig donar).
