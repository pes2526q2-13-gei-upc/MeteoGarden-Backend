from datetime import timedelta

import pytest
from django.utils import timezone

from api.models import (
    Event,
    EventsCategory,
    Garden,
    GrowthState,
    Plant,
    PlantInGarden,
    Pot,
    Station,
    User,
)


@pytest.fixture
def events_category(db):
    return EventsCategory.objects.create(name="Conciertos")


@pytest.mark.django_db
def test_cleanup_old_events(tmp_path, events_category):
    event = Event.objects.create(
        id="1",
        title="Old Event",
        subtitle="Old",
        description="Expired",
        start_date=timezone.now() - timedelta(days=31),
        end_date=timezone.now() - timedelta(days=31),
        category=events_category,
        price=10,
        tags=[],
        city="Barcelona",
        street="Carrer Major",
    )
    # Simula imagen si tienes ImageField
    if hasattr(event, "image") and event.image and hasattr(event.image, "save"):
        from django.core.files.base import ContentFile

        event.image.save("test.jpg", ContentFile(b"hola"), save=True)

    from api.tasks import cleanup_old_events

    msg = cleanup_old_events()
    assert "1" in msg
    assert not Event.objects.filter(id="1").exists()


@pytest.mark.django_db
def test_simulate_all_plants(monkeypatch):
    user = User.objects.create_user(
        username="plantuser",
        password="1",
        email="x@y.com",
        city="Barcelona",
        stationCode="ABC1",
    )
    station = Station.objects.create(
        stationCode="ABC1",
        station="North",
        city="Barcelona",
        solarIrradiance=100,
        temperature=22,
        windSpeed=1.2,
        relativeHumidity=45.0,
        precipitation=0.1,
    )
    plant = Plant.objects.create(
        scientificName="rose",
        minTemperature=0,
        maxTemperature=40,
    )
    garden = Garden.objects.create(user=user, name="Amb Jardí")
    pot = Pot.objects.create(garden=garden, number=1)
    plant_garden = PlantInGarden.objects.create(
        pot=pot,
        plant=plant,
        plantedAt=timezone.now(),
        growthPhase=GrowthState.SEED,
        healthLevel=100.0,
        waterLevel=100.0,
        lastWateredAt=timezone.now(),
        lastSimulatedAt=timezone.now(),
    )

    # Mocks
    monkeypatch.setattr("api.firebase.initialize_firebase", lambda: None)
    monkeypatch.setattr("api.plant_simulation.simulate_plant", lambda p, s: p)
    monkeypatch.setattr("api.services.xema_sync.ensure_station_synced", lambda s: None)
    monkeypatch.setattr("api.services.notifications.notify", lambda *a, **kw: None)
    monkeypatch.setattr(
        "api.services.notifications.can_send_notification", lambda u: False
    )

    from api.tasks import simulate_all_plants

    simulate_all_plants()  # No debe lanzar excepción
