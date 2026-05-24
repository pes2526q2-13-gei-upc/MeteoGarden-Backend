import logging
from datetime import timedelta

import requests
from celery import shared_task
from django.core.files.base import ContentFile
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from api.firebase import initialize_firebase
from api.models import (
    Event,
    EventsCategory,
    Garden,
    GrowthState,
    Station,
    WeatherReading,
)
from api.plant_simulation import simulate_plant
from api.services.events import get_events_from_service
from api.services.notifications import can_send_notification, notify
from api.services.xema_sync import ensure_station_synced

logger = logging.getLogger(__name__)


# Aquestes són totes les funcions que pot executar el celery
@shared_task
def simulate_all_plants():
    initialize_firebase()

    gardens = Garden.objects.select_related("user").all()

    for garden in gardens:
        simulate_garden_plants(garden)


def simulate_garden_plants(garden):
    user = garden.user
    station = get_user_station(user)

    if not station:
        return

    previous_reading = get_latest_weather_reading(station)

    # Actualitzar dades meteo
    ensure_station_synced(station)

    latest_reading = get_latest_weather_reading(station)

    if not latest_reading:
        return

    old_weather = build_weather_snapshot(previous_reading, latest_reading)
    current_weather = build_weather_snapshot(latest_reading, latest_reading)

    counters = simulate_alive_plants(garden, station, user)

    if send_plant_status_notification(user, counters):
        return

    send_weather_notification(user, old_weather, current_weather)


def get_user_station(user):
    return Station.objects.filter(stationCode=user.stationCode).first()


def get_latest_weather_reading(station):
    return WeatherReading.objects.filter(station=station).order_by("-timestamp").first()


def build_weather_snapshot(reading, fallback_reading):
    if not reading:
        reading = fallback_reading

    return {
        "temp": reading.temperature or 0,
        "rain": reading.precipitation or 0,
        "wind": reading.windSpeed or 0,
    }


def get_alive_pots(garden):
    return (
        garden.pot_set.exclude(plantingarden__isnull=True)
        .exclude(plantingarden__growthPhase=GrowthState.DEAD)
        .select_related("plantingarden__plant")
    )


def simulate_alive_plants(garden, station, user):
    counters = create_notification_counters()

    for pot in get_alive_pots(garden):
        simulate_single_plant(pot.plantingarden, station, user, counters)

    return counters


def create_notification_counters():
    return {
        "critical": 0,
        "water": 0,
        "health_drop": 0,
    }


def simulate_single_plant(plant_in_garden, station, user, counters):
    old_state = get_plant_state(plant_in_garden)

    updated = simulate_plant(plant_in_garden, station)
    updated.save()

    send_immediate_plant_notifications(user, updated, old_state)

    if can_send_notification(user):
        update_notification_counters(counters, updated, old_state)


def get_plant_state(plant_in_garden):
    return {
        "phase": plant_in_garden.growthPhase,
        "health": plant_in_garden.healthLevel,
        "water": plant_in_garden.waterLevel,
    }


def send_immediate_plant_notifications(user, updated, old_state):
    if plant_has_died(updated, old_state):
        notify(
            user,
            "💀 Plant died",
            f"Your {updated.plant.commonName} has died",
        )

    if plant_changed_phase(updated, old_state):
        notify(
            user,
            "🌱 New growth phase",
            f"Your {updated.plant.commonName} has reached {updated.growthPhase}",
        )


def plant_has_died(updated, old_state):
    return (
        updated.growthPhase == GrowthState.DEAD
        and old_state["phase"] != GrowthState.DEAD
    )


def plant_changed_phase(updated, old_state):
    return updated.growthPhase != old_state["phase"]


def update_notification_counters(counters, updated, old_state):
    if plant_became_critical(updated, old_state):
        counters["critical"] += 1

    if plant_health_dropped_fast(updated, old_state):
        counters["health_drop"] += 1

    if plant_needs_water(updated, old_state):
        counters["water"] += 1


def plant_became_critical(updated, old_state):
    return updated.healthLevel < 20 and old_state["health"] >= 20


def plant_health_dropped_fast(updated, old_state):
    return old_state["health"] - updated.healthLevel > 15


def plant_needs_water(updated, old_state):
    return updated.waterLevel < 20 and old_state["water"] >= 20


def send_plant_status_notification(user, counters):
    notification = get_plant_status_notification(counters)

    if not notification:
        return False

    title, body = notification
    notify(user, title, body)
    return True


def get_plant_status_notification(counters):
    if counters["critical"] == 1:
        return "⚠️ Plant in danger", "One plant is in critical condition"

    if counters["critical"] > 1:
        return (
            "⚠️ Plants in danger",
            f"{counters['critical']} plants are in critical condition",
        )

    if counters["health_drop"] == 1:
        return "📉 Sudden health drop", "One plant got worse quickly"

    if counters["health_drop"] > 1:
        return (
            "📉 Sudden health drops",
            f"{counters['health_drop']} plants got worse quickly",
        )

    if counters["water"] == 1:
        return "💧 Plant needs water", "One plant needs watering"

    if counters["water"] > 1:
        return (
            "💧 Plants need water",
            f"{counters['water']} plants need watering",
        )

    return None


def send_weather_notification(user, old_weather, current_weather):
    notification = get_weather_notification(old_weather, current_weather)

    if not notification:
        return

    title, body = notification
    notify(user, title, body)


def get_weather_notification(old_weather, current_weather):
    old_temp = old_weather["temp"]
    old_rain = old_weather["rain"]
    old_wind = old_weather["wind"]

    temp = current_weather["temp"]
    rain = current_weather["rain"]
    wind = current_weather["wind"]

    if old_temp < 38 and temp >= 38:
        return "🔥 Extreme heat", "High temperatures may damage your plants"

    if old_temp > 0 and temp <= 0:
        return "🥶 Frost warning", "Freezing temperatures may damage your plants"

    if old_rain < 40 and rain >= 40:
        return "🌧️ Heavy rain", "Heavy rain detected in your area"

    if old_wind < 50 and wind >= 50:
        return "💨 Strong wind", "Strong wind may damage your plants"

    return None


def _download_image(event_obj, url):
    if not url:
        return
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            file_name = url.split("/")[-1] or f"event_{event_obj.id}.jpg"
            event_obj.image.save(file_name, ContentFile(response.content), save=True)

    except Exception as e:
        logger.exception(f"Error downloading image for the event {event_obj.id}: {e}")


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

        city = loc.get("county")
        street = loc.get("street")

        if city is None:
            city = ""
        if street is None:
            street = ""

        defaults = {
            "title": item.get("title"),
            "subtitle": item.get("subtitle"),
            "description": item.get("description", ""),
            "start_date": parse_datetime(item.get("start_date")),
            "end_date": parse_datetime(item.get("end_date")),
            "category": category_obj,
            "price": int(float(item.get("price", 0))),
            "tags": item.get("tags", []),
            "city": city,
            "street": street,
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
        data = get_events_from_service(url=next_url) or {}
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
