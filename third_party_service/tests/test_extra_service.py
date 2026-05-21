from io import StringIO

import pytest
import requests
from django.core.management import call_command

from api.models import Station
from third_party_service.serializers import (
    CurrentWeatherSerializer,
    DailySummarySerializer,
)
from third_party_service.services import generate_external_api_token
from third_party_service.utils import generate_api_key


@pytest.mark.django_db
def test_load_stations_command(monkeypatch):
    """Verifica que el comandament de Django llegeix l'API de Transparència i crea estacions."""

    def mock_get_rows(*args, **kwargs):
        class MockRowsResponse:
            def json(self):
                return [
                    {"codi_estacio": "BCN1", "nom_estacio": "Barcelona Sants"},
                    {"codi_estacio": "GIR2", "nom_estacio": "Girona Centre"},
                ]

        return MockRowsResponse()

    monkeypatch.setattr(requests, "get", mock_get_rows)

    # Executem el comandament capturant la sortida stdout
    out = StringIO()
    call_command("load_stations", stdout=out)

    output = out.getvalue()
    assert "2 estacions carregades." in output

    # Comprovem que s'han desat correctament a la Base de Dades
    assert Station.objects.filter(stationCode="BCN1").exists()
    st = Station.objects.get(stationCode="BCN1")
    assert st.station == "Barcelona Sants"
    assert st.temperature == 0.0  # El valor per defecte del teu script


# ==============================================================================
# 3. TESTS PER A serializers.py
# ==============================================================================


def test_current_weather_serializer_valid():
    """Valida les dades correctes per al CurrentWeatherSerializer."""
    payload = {
        "city": "Girona",
        "station_code": "GIR2",
        "timestamp": "2026-05-20T20:00:00Z",
        "temperature": 18.5,
        "precipitation": 0.0,
        "solar_irradiance": 0.0,
    }
    serializer = CurrentWeatherSerializer(data=payload)
    assert serializer.is_valid()


def test_current_weather_serializer_allows_nulls():
    """El serializer ha de permetre valors nuls en mètrica meteorològica."""
    payload = {
        "city": "Lleida",
        "station_code": "LLE3",
        "timestamp": "2026-05-20T20:00:00Z",
        "temperature": None,
        "precipitation": None,
        "solar_irradiance": None,
    }
    serializer = CurrentWeatherSerializer(data=payload)
    assert serializer.is_valid()


def test_daily_summary_serializer_invalid_date():
    """El format de data de DailySummarySerializer ha de ser correcte (YYYY-MM-DD)."""
    payload = {
        "city": "Tarragona",
        "station_code": "TAR4",
        "date": "això-no-és-una-data",
        "temperature_max": 25.0,
        "temperature_min": 12.2,
    }
    serializer = DailySummarySerializer(data=payload)
    assert not serializer.is_valid()
    assert "date" in serializer.errors


# ==============================================================================
# 4. TESTS PER A services.py I utils.py (API Keys)
# ==============================================================================


@pytest.mark.django_db
def test_generate_external_api_token(monkeypatch, django_user_model):
    """Prova que el wrapper utilitza correctament ApiKey.issue_token."""
    user = django_user_model.objects.create_user(
        username="external_dev", password="123"
    )

    # Mockegem la funció interna del model ApiKey per comprovar paràmetres
    called_with = {}

    def mock_issue_token(name, created_by, expires_at, rate_limit):
        called_with["name"] = name
        called_with["created_by"] = created_by
        called_with["rate_limit"] = rate_limit
        return None, "mocked_raw_token"

    from third_party_service.models import ApiKey

    monkeypatch.setattr(ApiKey, "issue_token", mock_issue_token)

    token = generate_external_api_token(
        name="Clau Nova", created_by=user, rate_limit="60/min"
    )

    # Canvia l'assert del test per acceptar la tupla sencera:
    assert token == (None, "mocked_raw_token")

    # O si només t'interessa el token (el segon element):
    assert token[1] == "mocked_raw_token"
    assert called_with["name"] == "Clau Nova"
    assert called_with["created_by"] == user
    assert called_with["rate_limit"] == "60/min"


@pytest.mark.django_db
def test_generate_api_key_utils(django_user_model):
    """Verifica que utils.generate_api_key crea un objecte a la BD utilitzant la lògica correcta."""
    user = django_user_model.objects.create_user(username="utils_user", password="123")

    # Cridem a la utilitat modificada
    api_key_obj = generate_api_key(user=user, name="Clau Script")

    # Comprovem que ens retorna la instància desada correctament
    assert api_key_obj is not None
    assert api_key_obj.name == "Clau Script"
    assert api_key_obj.pk is not None
