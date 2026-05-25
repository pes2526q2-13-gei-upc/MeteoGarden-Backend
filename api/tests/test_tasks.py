from datetime import timedelta
from unittest.mock import MagicMock

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
    # 1. Fem el mock directament apuntant a com s'ha importat dins d'api.tasks
    monkeypatch.setattr("api.tasks.initialize_firebase", lambda: None)

    # La resta de mocks es mantenen igual
    monkeypatch.setattr("api.plant_simulation.simulate_plant", lambda p, s: p)
    monkeypatch.setattr("api.services.xema_sync.ensure_station_synced", lambda s: None)
    monkeypatch.setattr("api.services.notifications.notify", lambda *a, **kw: None)
    monkeypatch.setattr(
        "api.services.notifications.can_send_notification", lambda u: False
    )

    from api.tasks import simulate_all_plants

    simulate_all_plants()


@pytest.fixture
def base_garden_setup(db):
    # Crea l'escenari bàsic d'usuari, estació, planta, jardí, pot i planta en test
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
        plantedAt=timezone.now() - timedelta(days=2),
        growthPhase=GrowthState.SEED,
        healthLevel=100.0,
        waterLevel=100.0,
        lastWateredAt=timezone.now() - timedelta(days=1),
        lastSimulatedAt=timezone.now() - timedelta(hours=5),
    )
    return {
        "user": user,
        "station": station,
        "plant": plant,
        "garden": garden,
        "pot": pot,
        "plant_garden": plant_garden,
    }


@pytest.mark.django_db
def test_simulate_all_plants_alive_and_notification(monkeypatch, base_garden_setup):
    monkeypatch.setattr("api.tasks.initialize_firebase", lambda: None)
    monkeypatch.setattr("api.tasks.ensure_station_synced", lambda s: None)

    notified = []

    def fake_notify(user, title, body):
        print(f"DEBUG_MOCK [notify] CRIDAT: {title} - {body}")
        notified.append((user.username, title, body))

    # Mocks de notificacions
    monkeypatch.setattr("api.services.notifications.notify", fake_notify)
    monkeypatch.setattr("api.tasks.notify", fake_notify)
    monkeypatch.setattr(
        "api.services.notifications.can_send_notification", lambda u: True
    )
    monkeypatch.setattr("api.tasks.can_send_notification", lambda u: True)

    # Mock de simulació de planta (retornant una còpia)
    def fake_simulate_plant(plant_in_garden, station):
        print(
            f"DEBUG_MOCK [simulate_plant] Rebuda planta id={plant_in_garden.id} amb estat={plant_in_garden.growthPhase}"
        )
        from copy import copy

        simulated = copy(plant_in_garden)
        simulated.growthPhase = GrowthState.DEAD
        simulated.healthLevel = 0
        simulated.waterLevel = 0
        return simulated

    monkeypatch.setattr("api.plant_simulation.simulate_plant", fake_simulate_plant)
    monkeypatch.setattr("api.tasks.simulate_plant", fake_simulate_plant)

    # 1. 🌦️ SOLUCIÓ: Creem la lectura meteorològica que demana tasks.py per poder continuar
    from api.models import WeatherReading

    station = base_garden_setup["station"]
    WeatherReading.objects.create(
        station=station,
        timestamp=timezone.now(),
        temperature=22.0,
        precipitation=0.0,
        solarIrradiance=200.0,
        windSpeed=1.5,
        relativeHumidity=50.0,
    )

    # Preparem les dades inicials (La planta comença totalment viva)
    plant = base_garden_setup["plant_garden"]
    plant.growthPhase = GrowthState.SEED
    plant.healthLevel = 100
    plant.waterLevel = 100
    plant.save()

    pot = base_garden_setup["pot"]
    pot.refresh_from_db()

    # Importem i executem de forma neta
    from api.tasks import simulate_all_plants

    print("-> EXECUTANT: simulate_all_plants()")
    simulate_all_plants()

    print("\n--- SECCIÓ FINAL DEL TEST ---")
    print("NOTIFIEDS CAPTURATS:", notified)

    # Comprovem si s'ha guardat qualsevol notificació a la llista (sigui quin sigui el títol o idioma)
    assert len(notified) > 0, "No s'ha generat cap notificació durant la simulació."
    assert any(
        "die" in str(t).lower() or "mort" in str(t).lower() for (_, t, _) in notified
    ), "La notificació enviada no indica la mort de la planta."


@pytest.mark.django_db
def test_simulate_all_plants_excludes_dead(monkeypatch, base_garden_setup):
    # Mocks bàsics
    monkeypatch.setattr("api.tasks.initialize_firebase", lambda: None)
    monkeypatch.setattr("api.tasks.ensure_station_synced", lambda s: None)
    monkeypatch.setattr("api.tasks.notify", lambda *a, **kw: None)
    monkeypatch.setattr("api.tasks.can_send_notification", lambda u: False)

    # Planta morta abans de la simulació
    plant = base_garden_setup["plant_garden"]
    plant.growthPhase = GrowthState.DEAD
    plant.save()

    # La funció simulate_plant no hauria de ser cridada (es pot mockejar amb un comptador si vols)
    called = {}

    def fake_simulate_plant(plant_in_garden, station):
        called["count"] = called.get("count", 0) + 1
        return plant_in_garden

    monkeypatch.setattr("api.tasks.simulate_plant", fake_simulate_plant)

    from api.tasks import simulate_all_plants

    simulate_all_plants()
    # Les plantes mortes no es simulen
    assert not called  # No ha sigut cridada ni una vegada


@pytest.mark.django_db
def test_simulate_all_plants_no_station(monkeypatch, base_garden_setup):
    """Verifica que si l'usuari no té estació, el procés salta el jardí sense llançar errors."""
    monkeypatch.setattr("api.tasks.initialize_firebase", lambda: None)

    # Treiem la stationCode de l'usuari per simular que no té estació configurada
    user = base_garden_setup["garden"].user
    user.stationCode = ""
    user.save()

    from api.tasks import simulate_all_plants

    # No hauria de petar, simplement fer un 'return' net internament
    simulate_all_plants()


# 2. TEST: Excloure plantes que JA estaven mortes abans de començar
@pytest.mark.django_db
def test_simulate_all_plants_excludes_already_dead(monkeypatch, base_garden_setup):
    """Verifica que les plantes que ja estan en estat DEAD ni tan sols es llegeixen per a la simulació."""
    monkeypatch.setattr("api.tasks.initialize_firebase", lambda: None)
    monkeypatch.setattr("api.tasks.ensure_station_synced", lambda s: None)

    # Creem la lectura meteo obligatòria
    from api.models import WeatherReading

    station = base_garden_setup["station"]
    WeatherReading.objects.create(
        station=station,
        timestamp=timezone.now(),
        temperature=20.0,
        precipitation=0.0,
        solarIrradiance=100.0,
        windSpeed=1.0,
        relativeHumidity=50.0,
    )

    # Forcem que la planta de la BD ja estigui MORTA d'abans
    plant = base_garden_setup["plant_garden"]
    plant.growthPhase = GrowthState.DEAD
    plant.save()

    # Mockegem el simulate_plant amb un espia per veure si es crida
    spy_called = []

    def fake_simulate(plant_in_garden, station):
        spy_called.append(plant_in_garden.id)
        return plant_in_garden

    monkeypatch.setattr("api.tasks.simulate_plant", fake_simulate)

    from api.tasks import simulate_all_plants

    simulate_all_plants()

    # Com que estava DEAD, el filtre 'get_alive_pots' l'ha d'excloure i la llista de crides ha d'estar buida
    assert len(spy_called) == 0


# 1. TEST: Sincronització quan l'API externa respon sense cap resultat (llista buida)
@pytest.mark.django_db
def test_sync_events_task_empty_response(monkeypatch):
    """Verifica el funcionament de sync_events_task si l'API externa no té esdeveniments."""

    # Mockegem el servei extern perquè retorni l'estructura correcta però buida
    def fake_get_events(url=None):
        return {"results": [], "next": None}

    monkeypatch.setattr("api.tasks.get_events_from_service", fake_get_events)

    from api.tasks import sync_events_task

    result_msg = sync_events_task()

    # Comprovem que ens diu que ha processat 0 creats i 0 actualitzats
    assert "0 creats" in result_msg
    assert "0 actualitzats" in result_msg


# 2. TEST: Sincronització d'un esdeveniment nou de trinca
@pytest.mark.django_db
def test_sync_events_task_creates_new_event(monkeypatch):
    """Verifica que sync_events_task processa correctament un element nou i crea la seva categoria."""

    # Resposta simulada del servei extern amb l'estructura real del teu process_event_item
    def fake_get_events(url=None):
        return {
            "results": [
                {
                    "id": "gresca-777",
                    "title": "Concert de Primavera",
                    "subtitle": "Música Folk",
                    "description": "Un concert a l'aire lliure.",
                    "start_date": "2026-05-25T18:00:00Z",
                    "end_date": "2026-05-25T23:00:00Z",
                    "category": "Musica",  # Provarem que es creï sola de zero
                    "price": "15.50",
                    "tags": ["folk", "outdoor"],
                    "location": {"county": "Barcelonès", "street": "Passeig de Gràcia"},
                    "image_url": None,  # Evitem descàrregues reals a internet en el test
                }
            ],
            "next": None,
        }

    monkeypatch.setattr("api.tasks.get_events_from_service", fake_get_events)

    # Comprovem que no existeixen a la BD abans de començar
    assert not Event.objects.filter(id="gresca-777").exists()
    assert not EventsCategory.objects.filter(name="Musica").exists()

    from api.tasks import sync_events_task

    result_msg = sync_events_task()

    # 1. Validem el string que retorna la task
    assert "1 creats" in result_msg
    assert "0 actualitzats" in result_msg

    # 2. Validem que s'ha persistit correctament a la Base de Dades del test
    assert Event.objects.filter(id="gresca-777").exists()
    db_event = Event.objects.get(id="gresca-777")

    assert db_event.title == "Concert de Primavera"
    assert (
        db_event.city == "Barcelonès"
    )  # Comprova que agafa correctament loc.get("county")
    assert (
        db_event.category.name == "Musica"
    )  # Comprova el get_or_create_category intern
    assert db_event.price == 15  # Comprova el teu int(float(...))


# 3. TEST: Actualització d'un esdeveniment que ja existia prèviament
@pytest.mark.django_db
def test_sync_events_task_updates_existing_event(monkeypatch):
    """Verifica que si l'esdeveniment ja existia, update_or_create actualitza els camps i augmenta el comptador d'updated."""

    cat = EventsCategory.objects.create(name="Teatre")
    # Creem l'esdeveniment antic a la base de dades
    Event.objects.create(
        id="gresca-111",
        title="Títol Antic",
        subtitle="Sub",
        description="Desc",
        start_date=timezone.now(),
        end_date=timezone.now() + timedelta(hours=2),
        category=cat,
        price=5,
        tags=[],
        city="Girona",
        street="Carrer de la Rutlla",
    )

    # El servei ara ens envia el mateix ID però amb canvis al títol i preu
    def fake_get_events(url=None):
        return {
            "results": [
                {
                    "id": "gresca-111",
                    "title": "Títol Super Actualitzat",
                    "subtitle": "Sub",
                    "description": "Desc",
                    "start_date": "2026-06-10T20:00:00Z",
                    "end_date": "2026-06-10T22:00:00Z",
                    "category": "Teatre",
                    "price": "25.00",
                    "tags": [],
                    "location": {"county": "Gironès", "street": "Carrer Nou"},
                    "image_url": None,
                }
            ],
            "next": None,
        }

    monkeypatch.setattr("api.tasks.get_events_from_service", fake_get_events)

    from api.tasks import sync_events_task

    result_msg = sync_events_task()

    # Validem els comptadors de retorn (0 creats, 1 actualitzat)
    assert "0 creats" in result_msg
    assert "1 actualitzats" in result_msg

    # Mirem si a la BD s'ha guardat el canvi de veritat
    updated_event = Event.objects.get(id="gresca-111")
    assert updated_event.title == "Títol Super Actualitzat"
    assert updated_event.price == 25
    assert updated_event.city == "Gironès"


@pytest.mark.django_db
def test_sync_events_image_download_failure_logs_exception(monkeypatch, caplog):
    """Verifica que si la descàrrega de la imatge falla (ex: Timeout), la task no peta, captura el log i continua creant l'esdeveniment."""

    import requests

    def fake_get_failing_image(url, timeout=None):
        raise requests.exceptions.Timeout("Connection timed out")

    monkeypatch.setattr("requests.get", fake_get_failing_image)

    def fake_get_events(url=None):
        return {
            "results": [
                {
                    "id": "gresca-img-fail",
                    "title": "Esdeveniment amb Foto Falsa",
                    "subtitle": "Sub",
                    "description": "Desc",
                    "start_date": "2026-05-25T18:00:00Z",  # 🔥 SOLUCIÓ: Afegim les dates obligatòries
                    "end_date": "2026-05-25T23:00:00Z",  # 🔥 SOLUCIÓ: Afegim les dates obligatòries
                    "category": "Festa",
                    "price": "10.00",
                    "location": {"county": "Lleida"},
                    "image_url": "https://imatge-falsa.com/foto.jpg",
                }
            ],
            "next": None,
        }

    monkeypatch.setattr("api.tasks.get_events_from_service", fake_get_events)

    from api.tasks import sync_events_task

    with caplog.at_level("ERROR"):
        result_msg = sync_events_task()

    assert Event.objects.filter(id="gresca-img-fail").exists()
    assert "Error downloading image for the event" in caplog.text

    @pytest.mark.django_db
    def test_simulate_all_plants_growth_phase_change_notification(
        monkeypatch, base_garden_setup
    ):
        """Verifica que si la planta canvia de fase (ex: SEED -> GERMINATION), es genera la notificació🌱."""
        monkeypatch.setattr("api.tasks.initialize_firebase", lambda: None)
        monkeypatch.setattr("api.tasks.ensure_station_synced", lambda s: None)

        notified = []
        monkeypatch.setattr("api.tasks.notify", lambda u, t, b: notified.append((t, b)))
        monkeypatch.setattr("api.tasks.can_send_notification", lambda u: True)

        # Mock que simula el canvi pur de fase de SEED a una altra vàlida
        def fake_simulate_phase(plant_in_garden, station):
            from copy import copy

            simulated = copy(plant_in_garden)
            simulated.growthPhase = "GERMINATION"  # Canvi d'estat pur
            return simulated

        monkeypatch.setattr("api.tasks.simulate_plant", fake_simulate_phase)

        # Forcem la lectura climàtica inicial bàsica
        from api.models import WeatherReading

        WeatherReading.objects.create(
            station=base_garden_setup["station"],
            timestamp=timezone.now(),
            temperature=20.0,
            precipitation=0.0,
            solarIrradiance=100.0,
            windSpeed=1.0,
            relativeHumidity=50.0,
        )

        from api.tasks import simulate_all_plants

        simulate_all_plants()

        assert any("New growth phase" in t for (t, _) in notified)


@pytest.mark.django_db
def test_simulate_all_plants_status_counters_logic(monkeypatch, base_garden_setup):
    """Verifica que el sistema acumula correctament els avisos de perill de salut i aigua baixa."""
    monkeypatch.setattr("api.tasks.initialize_firebase", lambda: None)
    monkeypatch.setattr("api.tasks.ensure_station_synced", lambda s: None)

    notified = []
    monkeypatch.setattr("api.tasks.notify", lambda u, t, b: notified.append((t, b)))
    monkeypatch.setattr("api.tasks.can_send_notification", lambda u: True)

    # Forcem que la planta passi de 100 de vida/aigua a valors crítics (< 20) i caiguda ràpida (> 15)
    def fake_simulate_critical(plant_in_garden, station):
        from copy import copy

        simulated = copy(plant_in_garden)
        simulated.healthLevel = 10  # Ha caigut un 90% (més de 15) i està a menys de 20
        simulated.waterLevel = 5  # Menys de 20
        return simulated

    monkeypatch.setattr("api.tasks.simulate_plant", fake_simulate_critical)

    from api.models import WeatherReading

    WeatherReading.objects.create(
        station=base_garden_setup["station"],
        timestamp=timezone.now(),
        temperature=20.0,
        precipitation=0.0,
        solarIrradiance=100.0,
        windSpeed=1.0,
        relativeHumidity=50.0,
    )

    from api.tasks import simulate_all_plants

    simulate_all_plants()

    # Com que send_plant_status_notification es llança i retorna True,
    # s'haurà enviat l'alerta crítica de salut/perill prioritària.
    assert any(
        "danger" in t.lower() or "drop" in t.lower() or "water" in t.lower()
        for (t, _) in notified
    )


@pytest.mark.django_db
def test_weather_notification_alerts(monkeypatch, base_garden_setup):
    """Verifica que es disparen les alertes de clima extrem (Calor extrema) quan hi ha un pic tèrmic."""
    monkeypatch.setattr("api.tasks.initialize_firebase", lambda: None)

    # 1. 🌦️ SOLUCIÓ: El mock de sync afegeix la lectura de calor extrema dinàmicament quan es crida
    from api.models import WeatherReading

    station = base_garden_setup["station"]

    def fake_ensure_station_synced(s):
        WeatherReading.objects.create(
            station=station,
            timestamp=timezone.now(),
            temperature=39.0,
            precipitation=0.0,
            solarIrradiance=100.0,
            windSpeed=1.0,
            relativeHumidity=50.0,
        )

    monkeypatch.setattr("api.tasks.ensure_station_synced", fake_ensure_station_synced)

    notified = []
    monkeypatch.setattr("api.tasks.notify", lambda u, t, b: notified.append((t, b)))
    monkeypatch.setattr("api.tasks.can_send_notification", lambda u: True)

    # Ens interessa que la planta NO canviï d'estat ni perdi salut per no aixafar la notificació del clima
    monkeypatch.setattr("api.tasks.simulate_plant", lambda p, s: p)

    # Creem NOMÉS la lectura prèvia suau (25 graus) abans de començar la task
    WeatherReading.objects.create(
        station=station,
        timestamp=timezone.now() - timedelta(minutes=10),
        temperature=25.0,
        precipitation=0.0,
        solarIrradiance=100.0,
        windSpeed=1.0,
        relativeHumidity=50.0,
    )

    from api.tasks import simulate_all_plants

    simulate_all_plants()

    # Validem si s'ha interceptat l'alerta climàtica de calor
    assert any("Extreme heat" in t for (t, _) in notified)


@pytest.mark.django_db
def test_get_or_create_category_empty_or_none():
    """Verifica que si la categoria és None o un text buit, retorna None sense fallar."""
    from api.tasks import get_or_create_category

    assert get_or_create_category(None) is None
    assert get_or_create_category("") is None


@pytest.mark.django_db
def test_get_or_create_category_strips_whitespace():
    """Verifica que neteja els espais en blanc extrems i crea o obté la categoria."""
    from api.tasks import get_or_create_category

    assert not EventsCategory.objects.filter(name="Concerts").exists()

    cat = get_or_create_category("  Concerts   ")
    assert cat.name == "Concerts"
    assert EventsCategory.objects.filter(name="Concerts").count() == 1

    # Si la tornem a demanar, l'ha de recuperar en comptes de duplicar-la
    cat_repetida = get_or_create_category("Concerts")
    assert cat_repetida.id == cat.id


@pytest.mark.django_db
def test_update_event_image_no_url(events_category):
    """Verifica que si no hi ha image_url, no intenta fer cap descàrrega."""
    from api.tasks import update_event_image

    event = Event.objects.create(
        id="test-no-img",
        title="Sense imatge",
        category=events_category,
        start_date=timezone.now(),
        end_date=timezone.now(),
        price=0,
        city="",
    )

    item = {"image_url": None}
    # Si intentés descarregar, petaria perquè no hem mockejat requests.get
    update_event_image(event, item, created=True)
    assert not event.image


@pytest.mark.django_db
def test_process_event_item_handles_missing_location(monkeypatch, events_category):
    """Verifica que process_event_item gestiona correctament l'absència de 'location'

    o valors None, guardant strings buits com a fallback.
    """
    from api.tasks import process_event_item

    # Simulem un item que ve del servei extern sense adreça ni comtat ni imatge
    item = {
        "id": "test-fallback-loc",
        "title": "Esdeveniment Minimalista",
        "subtitle": "Sub",
        "description": "Desc",
        "start_date": "2026-05-25T18:00:00Z",
        "end_date": "2026-05-25T23:00:00Z",
        "category": "Concerts",
        "price": "0.00",
        "tags": [],
        "location": {},  # Buit per provar el fallback del .get() o ""
        "image_url": None,
    }

    created = process_event_item(item)
    assert created is True

    db_event = Event.objects.get(id="test-fallback-loc")
    assert db_event.city == ""
    assert db_event.street == ""


@pytest.mark.django_db
def test_sync_events_task_pagination_loop(monkeypatch):
    """Test crucial per a SonarCloud: verifica que el bucle 'while True' de paginació

    itera correctament mentre hi hagi un 'next' i es deté de forma neta.
    """
    call_tracker = {"page": 1}

    def fake_get_events_paginated(url=None):
        # Primera pàgina: retorna un element i un enllaç a la següent pàgina
        if call_tracker["page"] == 1:
            call_tracker["page"] += 1
            return {
                "results": [
                    {
                        "id": "pag-1",
                        "title": "Ev Pàgina 1",
                        "subtitle": "",
                        "category": "Festa",
                        "start_date": "2026-05-25T18:00:00Z",
                        "end_date": "2026-05-25T23:00:00Z",
                        "price": "10",
                        "location": {"county": "BCN"},
                    }
                ],
                "next": "https://api-externa.com/events/?page=2",
            }
        # Segona pàgina: retorna un element però ja no hi ha més pàgines (next=None)
        elif call_tracker["page"] == 2:
            call_tracker["page"] += 1
            return {
                "results": [
                    {
                        "id": "pag-2",
                        "title": "Ev Pàgina 2",
                        "subtitle": "",
                        "category": "Festa",
                        "start_date": "2026-05-25T18:00:00Z",
                        "end_date": "2026-05-25T23:00:00Z",
                        "price": "12",
                        "location": {"county": "GIR"},
                    }
                ],
                "next": None,
            }
        # Per seguretat, si tornés a demanar, buit
        return {"results": [], "next": None}

    monkeypatch.setattr("api.tasks.get_events_from_service", fake_get_events_paginated)

    from api.tasks import sync_events_task

    result_msg = sync_events_task()

    # Comprovem que ha fet les dues iteracions i ha sumat correctament ambdós registres de les dues pàgines
    assert "2 creats" in result_msg
    assert "0 actualitzats" in result_msg
    assert Event.objects.filter(id="pag-1").exists()
    assert Event.objects.filter(id="pag-2").exists()
