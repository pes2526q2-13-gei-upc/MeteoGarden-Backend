import logging
from datetime import timedelta

import requests
from celery import shared_task
from django.core.files.base import ContentFile
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from api.firebase import initialize_firebase
from api.models import Event, Garden, GrowthState, Station
from api.notifications import can_send_notification, send_push_notification
from api.plant_simulation import simulate_plant
from api.services.events import getEventsFromService
from api.services.xema_sync import ensure_station_synced

logger = logging.getLogger(__name__)

# Aquestes són totes les funcions que pot executar el celery


@shared_task
def simulate_all_plants():
    initialize_firebase()
    gardens = Garden.objects.select_related("user").all()

    for garden in gardens:
        user = garden.user

        station = Station.objects.filter(stationCode=user.stationCode).first()

        if not station:
            continue

        # Actualitzar dades meteo
        ensure_station_synced(station)

        # Agafa totes les plantes vives
        pots = (
            garden.pot_set.exclude(plantingarden__isnull=True)
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
                    f"{updated.plant.commonName} està molt malament",
                )
                updated.lastNotificationAt = timezone.now()
                updated.save()
                continue

            # terminal
            if updated.healthLevel < 20 and old_health >= 20:
                print(
                    f"NOTIFICACIÓ: {user.username}, la teva planta {pig.plant.commonName} està molt malalta!"
                )

            # Planta morta
            if updated.growthPhase == GrowthState.DEAD:
                send_push_notification(
                    user,
                    "💀 Planta morta",
                    f"La teva planta {updated.plant.commonName} ha mort",
                )
                updated.lastNotificationAt = timezone.now()
                updated.save()
                continue

            # terminal
            if (
                updated.growthPhase == GrowthState.DEAD
                and old_phase != GrowthState.DEAD
            ):
                print(
                    f"NOTIFICACIÓ: {user.username}, la teva planta {pig.plant.commonName} ha mort."
                )

            # Planta canvia de fase
            if updated.growthPhase != old_phase:
                send_push_notification(
                    user,
                    "🌱 Nova fase",
                    f"{updated.plant.commonName} ha evolucionat a {updated.growthPhase}",
                )
                updated.lastNotificationAt = timezone.now()
                updated.save()
                continue
            # terminal
            if updated.growthPhase != old_phase:
                print(
                    f"NOTIFICACIÓ: {user.username}, la planta {pig.plant.commonName} ha passat a fase {pig.growthPhase}!"
                )

            # caiguda brusca salut
            if old_health - updated.healthLevel > 15:
                send_push_notification(
                    user,
                    "Canvi brusc de salut",
                    f"{updated.plant.commonName} ha empitjorat ràpidament",
                )
                updated.lastNotificationAt = timezone.now()
                updated.save()
                continue

            # 💧 Falta aigua
            if updated.waterLevel < 20:
                send_push_notification(
                    user, "💧 Necessita aigua", "Una planta necessita reg!"
                )
                updated.lastNotificationAt = timezone.now()
                updated.save()


def _download_image(event_obj, url):
    if not url:
        return
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            file_name = url.split("/")[-1] or f"event_{event_obj.id}.jpg"
            event_obj.image.save(file_name, ContentFile(response.content), save=True)

    except Exception as e:
        logger.error(f"Error downloading image for the event {event_obj.id}: {e}")


@shared_task(name="sync_events_task")
def sync_events_task():
    next_url = None
    total_created = 0
    total_updated = 0

    while True:
        data = getEventsFromService(url=next_url)
        if not data or "results" not in data:
            break

        for item in data["results"]:
            loc = item.get("location", {})

            event, created = Event.objects.update_or_create(
                id=item.get("id"),
                defaults={
                    "title": item.get("title"),
                    "subtitle": item.get("subtitle"),
                    "description": item.get("description", ""),
                    "start_date": parse_datetime(item.get("start_date")),
                    "end_date": parse_datetime(item.get("end_date")),
                    "category": item.get("category"),
                    "price": int(float(item.get("price", 0))),
                    "tags": item.get("tags", []),
                    "city": loc.get("county", "Desconeguda"),
                    "street": loc.get("street", ""),
                },
            )

            new_image = item.get("image_url")
            if new_image:
                if created or not event.image:
                    _download_image(event, new_image)

            if created:
                total_created += 1
            else:
                total_updated += 1

        next_url = data.get("next")
        if not next_url:
            break

    return f"Sincronització completa: {total_created} creats, {total_updated} actualitzats."


@shared_task(name="cleanup_old_events")
def cleanup_old_events():
    # 1. Calculem la data límit (ara fa 30 dies)
    # Fem servir timezone.now() segons el que veig al teu settings.py
    cutoff_date = timezone.now() - timedelta(days=30)

    # 2. Busquem els esdeveniments caducats
    old_events = Event.objects.filter(end_date__lt=cutoff_date)
    count = old_events.count()

    for event in old_events:
        # 3. Esborrem la imatge de l'S3 primer
        # El mètode .delete(save=False) del camp ImageField esborra el fitxer al núvol
        if event.image:
            event.image.delete(save=False)

        # 4. Esborrem el registre de la base de dades
        event.delete()

    return (
        f"Neteja completada: s'han eliminat {count} esdeveniments i les seves imatges."
    )
