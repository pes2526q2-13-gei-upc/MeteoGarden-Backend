import logging
from datetime import timedelta

import requests
from celery import shared_task
from django.core.files.base import ContentFile
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from api.firebase import initialize_firebase
from api.models import Event, Garden, GrowthState, Station, WeatherReading
from api.notifications import can_send_notification, notify
from api.models import Event, EventsCategory, Garden, GrowthState, Station
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

        previous_reading = (
            WeatherReading.objects.filter(station=station)
            .order_by("-timestamp")
            .first()
        )

        # Actualitzar dades meteo
        ensure_station_synced(station)

        latest_reading = (
            WeatherReading.objects.filter(station=station)
            .order_by("-timestamp")
            .first()
        )

        if not latest_reading:
            continue

        temp = latest_reading.temperature or 0
        rain = latest_reading.precipitation or 0
        wind = latest_reading.windSpeed or 0

        old_temp = previous_reading.temperature if previous_reading else temp
        old_rain = previous_reading.precipitation if previous_reading else rain
        old_wind = previous_reading.windSpeed if previous_reading else wind

        # Agafa totes les plantes vives
        pots = (
            garden.pot_set.exclude(plantingarden__isnull=True)
            .exclude(plantingarden__growthPhase=GrowthState.DEAD)
            .select_related("plantingarden__plant")
        )
        critical_count = 0
        water_count = 0
        health_drop_count = 0

        # Simula cada planta
        for pot in pots:
            pig = pot.plantingarden
            old_phase = pig.growthPhase
            old_health = pig.healthLevel
            old_water = pig.waterLevel

            updated = simulate_plant(pig, station)
            updated.save()

            # Notificacions sempre
            # Planta morta
            if (
                updated.growthPhase == GrowthState.DEAD
                and old_phase != GrowthState.DEAD
            ):
                notify(
                    user, "💀 Plant died", f"Your {updated.plant.commonName} has died"
                )

            # Planta canvia de fase
            if updated.growthPhase != old_phase:
                notify(
                    user,
                    "🌱 New growth phase",
                    f"Your {updated.plant.commonName} has reached {updated.growthPhase}",
                )

            # Notificacions cooldown en ordre de prioritat
            if not can_send_notification(user):
                continue

            # Planta baixa de salut
            if updated.healthLevel < 20 and old_health >= 20:
                critical_count += 1

            # caiguda brusca salut
            if old_health - updated.healthLevel > 15:
                health_drop_count += 1

            # Falta aigua
            if updated.waterLevel < 20 and old_water >= 20:
                water_count += 1

        if critical_count == 1:
            notify(user, "⚠️ Plant in danger", "One plant is in critical condition")
            continue

        elif critical_count > 1:
            notify(
                user,
                "⚠️ Plants in danger",
                f"{critical_count} plants are in critical condition",
            )
            continue

        if health_drop_count == 1:
            notify(user, "📉 Sudden health drop", "One plant got worse quickly")
            continue

        elif health_drop_count > 1:
            notify(
                user,
                "📉 Sudden health drops",
                f"{health_drop_count} plants got worse quickly",
            )
            continue

        if water_count == 1:
            notify(user, "💧 Plant needs water", "One plant needs watering")
            continue

        elif water_count > 1:
            notify(user, "💧 Plants need water", f"{water_count} plants need watering")
            continue

        if old_temp < 38 and temp >= 38:
            notify(user, "🔥 Extreme heat", "High temperatures may damage your plants")
            continue

        elif old_temp > 0 and temp <= 0:
            notify(
                user, "🥶 Frost warning", "Freezing temperatures may damage your plants"
            )
            continue

        elif old_rain < 40 and rain >= 40:
            notify(user, "🌧️ Heavy rain", "Heavy rain detected in your area")
            continue

        elif old_wind < 50 and wind >= 50:
            notify(user, "💨 Strong wind", "Strong wind may damage your plants")
            continue


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


@shared_task()
def sync_events_task():
    def get_or_create_category(category_name):
        if not category_name:
            return None
        return EventsCategory.objects.get_or_create(name=category_name.strip())[0]

    def update_event_image(event, item, created):
        """Extracted branching logic to reduce complexity in the main process."""
        new_image = item.get("image_url")
        if new_image and (created or not event.image):
            _download_image(event, new_image)

    def process_event_item(item):
        loc = item.get("location", {})
        category_obj = get_or_create_category(item.get("category"))

        defaults = {
            "title": item.get("title"),
            "subtitle": item.get("subtitle"),
            "description": item.get("description", ""),
            "start_date": parse_datetime(item.get("start_date")),
            "end_date": parse_datetime(item.get("end_date")),
            "category": category_obj,
            "price": int(float(item.get("price", 0))),
            "tags": item.get("tags", []),
            "city": loc.get("county", "Desconeguda"),
            "street": loc.get("street", ""),
        }

        event, created = Event.objects.update_or_create(
            id=item.get("id"), defaults=defaults
        )
        update_event_image(event, item, created)
        return created

    next_url = None
    counts = {"created": 0, "updated": 0}

    # Use a cleaner loop structure to avoid multiple 'break' conditions
    active = True
    while active:
        data = getEventsFromService(url=next_url) or {}
        results = data.get("results", [])

        for item in results:
            is_new = process_event_item(item)
            counts["created" if is_new else "updated"] += 1

        next_url = data.get("next")
        active = bool(next_url and results)

    return f"Sincronització completa: {counts['created']} creats, {counts['updated']} actualitzats."


@shared_task()
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
