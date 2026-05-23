import pytest
from rest_framework.test import APIClient

from api.models import Station, WeatherReading
from third_party_service.models import ApiKey


@pytest.fixture
def user(db, django_user_model):
    return django_user_model.objects.create_user(
        username="testuser",
        password="secret",
        email="a@b.com",
        city="Barcelona",
        stationCode="BAR1",
    )


@pytest.fixture
def api_key(user):
    obj, token = ApiKey.issue_token(name="Test Key", created_by=user)
    return token


@pytest.fixture
def client(api_key):
    c = APIClient()
    c.credentials(HTTP_X_API_KEY=api_key)
    return c


@pytest.fixture
def station(db):
    return Station.objects.create(
        stationCode="BAR1",
        station="Estació Centre",
        city="Barcelona",
        solarIrradiance=123,
        temperature=20.5,
        windSpeed=2.0,
        relativeHumidity=60.0,
        precipitation=1.5,
    )


@pytest.fixture
def reading(station):
    return WeatherReading.objects.create(
        station=station,
        timestamp="2026-05-20T13:00:00Z",
        temperature=23.4,
        precipitation=0.8,
        solarIrradiance=123,
        windSpeed=2.0,
        relativeHumidity=60.0,
    )


@pytest.fixture
def staff_user(db, django_user_model):
    return django_user_model.objects.create_user(
        username="staff",
        password="adminsecret",
        email="admin@a.com",
        city="Madrid",
        stationCode="MAD1",
        is_staff=True,
    )


@pytest.mark.django_db
def test_current_weather_success(monkeypatch, client, station, reading):
    monkeypatch.setattr(
        "api.services.xema_sync.ensure_station_synced", lambda station: None
    )
    response = client.get("/third-party-service/weather/current/?city=Barcelona")
    assert response.status_code == 200
    data = response.json()
    assert data["city"].lower() == "barcelona"
    assert data["temperature"] == pytest.approx(23.4)
    assert data["precipitation"] == pytest.approx(0.8)
    assert data["solarIrradiance"] == 123


@pytest.mark.django_db
def test_current_weather_city_required(monkeypatch, client):
    monkeypatch.setattr("api.services.xema_sync.ensure_station_synced", lambda s: None)
    r = client.get("/third-party-service/weather/current/")
    assert r.status_code == 400
    assert "city" in r.json()["error"]


@pytest.mark.django_db
def test_current_weather_station_not_found(monkeypatch, client):
    monkeypatch.setattr("api.services.xema_sync.ensure_station_synced", lambda s: None)
    r = client.get("/third-party-service/weather/current/?city=UnknownCity")
    assert r.status_code == 404


@pytest.mark.django_db
def test_current_weather_no_data(monkeypatch, client, station):
    monkeypatch.setattr("api.services.xema_sync.ensure_station_synced", lambda s: None)
    r = client.get("/third-party-service/weather/current/?city=Barcelona")
    assert r.status_code == 503


@pytest.mark.django_db
def test_daily_weather_success(monkeypatch, client, station, reading):
    monkeypatch.setattr("api.services.xema_sync.ensure_station_synced", lambda s: None)
    monkeypatch.setattr(
        "api.services.xema_sync._fetch_and_save", lambda s, since, until: None
    )
    date_str = "2026-05-20"
    r = client.get(
        f"/third-party-service/weather/daily/?city=Barcelona&date={date_str}"
    )
    assert r.status_code == 200
    d = r.json()
    assert d["city"].lower() == "barcelona"
    assert d["date"] == date_str
    assert d["temperatureMax"] == 23.4
    assert d["temperatureMin"] == 23.4


@pytest.mark.django_db
def test_daily_weather_future_date(monkeypatch, client, station):
    import datetime

    monkeypatch.setattr("api.services.xema_sync.ensure_station_synced", lambda s: None)
    future = (datetime.date.today() + datetime.timedelta(days=3)).isoformat()
    r = client.get(f"/third-party-service/weather/daily/?city=Barcelona&date={future}")
    assert r.status_code == 400
    assert "Cannot query future dates" in r.json()["error"]


@pytest.mark.django_db
def test_daily_weather_missing_params(client):
    r = client.get("/third-party-service/weather/daily/")
    assert r.status_code == 400
    assert "city" in r.json()["error"]


@pytest.mark.django_db
def test_daily_weather_invalid_date(client, station):
    r = client.get("/third-party-service/weather/daily/?city=Barcelona&date=notadate")
    assert r.status_code == 400
    assert "Invalid date" in r.json()["error"]


@pytest.mark.django_db
def test_daily_weather_station_not_found(client):
    r = client.get("/third-party-service/weather/daily/?city=NoCity&date=2024-01-01")
    assert r.status_code == 404


from datetime import date, datetime, timedelta
from datetime import timezone as dt_timezone


@pytest.mark.django_db
def test_daily_weather_fetch_if_no_data(monkeypatch, client, station):
    date_str = "2026-05-20"
    target_day = datetime.strptime(date_str, "%Y-%m-%d").date()
    created = {}

    def mock_fetch_and_save(station_arg, since, until):
        # Force the timestamp to be within the queried range (2026-05-20)
        # instead of strictly relying on since.date() matching exactly
        target_timestamp = datetime(
            target_day.year,
            target_day.month,
            target_day.day,
            12,
            0,
            tzinfo=dt_timezone.utc,
        )

        created["done"] = True
        WeatherReading.objects.create(
            station=station_arg,
            timestamp=target_timestamp,  # Ensured to fall within day_start and day_end
            temperature=27.0,
            precipitation=0.5,
            solarIrradiance=101,
            windSpeed=1,
            relativeHumidity=55,
        )

    monkeypatch.setattr("api.services.xema_sync.ensure_station_synced", lambda s: None)
    monkeypatch.setattr("api.services.xema_sync._fetch_and_save", mock_fetch_and_save)

    r = client.get(
        f"/third-party-service/weather/daily/?city=Barcelona&date={date_str}"
    )

    assert r.status_code == 200
    d = r.json()
    assert d["temperatureMax"] == 27.0
    assert d["temperatureMin"] == 27.0
    assert "done" in created


@pytest.mark.django_db
def test_get_stations_for_city_found(client, station):
    r = client.get("/third-party-service/stations/?city=Barcelona")
    assert r.status_code == 200
    assert "cities" in r.json()
    assert {"city": "Barcelona"} in r.json()["cities"]


@pytest.mark.django_db
def test_get_stations_for_city_not_found(client):
    r = client.get("/third-party-service/stations/?city=NoExist")
    assert r.status_code == 404


@pytest.mark.django_db
def test_get_stations_city_required(client):
    r = client.get("/third-party-service/stations/")
    assert r.status_code == 400


@pytest.mark.django_db
def test_register_and_get_key_success(staff_user):
    client = APIClient()
    client.force_authenticate(user=staff_user)
    payload = {
        "username": "newuser",
        "email": "new@b.com",
        "password": "secretpass",
        "key_name": "PRIMERA",
    }
    r = client.post("/third-party-service/register/", payload, format="json")
    assert r.status_code == 201
    data = r.json()
    assert "api_key" in data
    assert data["username"] == "newuser"


@pytest.mark.django_db
def test_register_and_get_key_missing_fields(staff_user):
    client = APIClient()
    client.force_authenticate(user=staff_user)
    payload = {"username": "", "email": "", "password": ""}
    r = client.post("/third-party-service/register/", payload, format="json")
    assert r.status_code == 400


@pytest.mark.django_db
def test_register_and_get_key_username_taken(staff_user, user):
    client = APIClient()
    client.force_authenticate(user=staff_user)
    payload = {"username": "testuser", "email": "diff@b.com", "password": "123456"}
    r = client.post("/third-party-service/register/", payload, format="json")
    assert r.status_code == 400
    assert "ja està agafat" in r.json()["error"]


@pytest.mark.django_db
def test_login_and_generate_key_success(user):
    client = APIClient()
    from django.contrib.auth import get_user_model

    get_user_model().objects.filter(username="testuser").update(is_active=True)
    payload = {"username": "testuser", "password": "secret", "key_name": "Sessió Test"}
    r = client.post("/third-party-service/login/", payload, format="json")
    assert r.status_code == 200
    assert "api_key" in r.json()
    assert r.json()["status"] == "Login correcte"


@pytest.mark.django_db
def test_login_and_generate_key_wrong_password(user):
    client = APIClient()
    payload = {"username": "testuser", "password": "wrongpass"}
    r = client.post("/third-party-service/login/", payload, format="json")
    assert r.status_code == 401


@pytest.mark.django_db
def test_login_and_generate_key_inactive(user):
    client = APIClient()
    from django.contrib.auth import get_user_model

    get_user_model().objects.filter(username="testuser").update(is_active=False)
    payload = {"username": "testuser", "password": "secret"}
    r = client.post("/third-party-service/login/", payload, format="json")
    assert r.status_code == 401
    assert "error" in r.json()
    assert "Credencials incorrectes" in r.json()["error"]
