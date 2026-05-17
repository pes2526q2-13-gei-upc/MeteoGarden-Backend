from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from api.models import Station, WeatherReading
from api.services.xema_sync import (
    _build_fields,
    _cleanup_old_readings,
    _fetch_and_save,
    ensure_station_synced,
)


@pytest.mark.django_db
class TestXemaSync:

    def create_station(self):
        return Station.objects.create(
            stationCode="1234",
            station="Test",
            city="Test",
            solarIrradiance=0,
            temperature=0,
            windSpeed=0,
            relativeHumidity=0,
            precipitation=0,
        )

    def test_build_fields_full(self):
        codes = {"32": 20, "35": 1, "33": 60, "46": 5}

        fields = _build_fields(codes)

        assert fields["temperature"] == 20
        assert fields["precipitation"] == 1
        assert fields["relativeHumidity"] == 60
        assert fields["windSpeed"] == 5

    def test_build_fields_no_wind(self):
        fields = _build_fields({})

        assert "windSpeed" not in fields

    @patch("api.services.xema_sync.requests.get")
    def test_fetch_invalid_response(self, mock_get):
        station = self.create_station()

        mock_get.return_value.json.return_value = {"error": "bad"}

        result = _fetch_and_save(
            station, timezone.now() - timedelta(hours=1), timezone.now()
        )

        assert result == 0

    @patch("api.services.xema_sync.requests.get")
    def test_fetch_exception(self, mock_get):
        station = self.create_station()

        mock_get.side_effect = Exception("boom")

        result = _fetch_and_save(
            station, timezone.now() - timedelta(hours=1), timezone.now()
        )

        assert result == 0

    @patch("api.services.xema_sync.requests.get")
    def test_fetch_ignores_invalid_rows(self, mock_get):
        station = self.create_station()

        mock_get.return_value.json.return_value = [
            {"bad": "data"},
            {"data_lectura": "", "codi_variable": "32", "valor_lectura": "20"},
        ]

        result = _fetch_and_save(
            station, timezone.now() - timedelta(hours=1), timezone.now()
        )

        assert result == 0

    def test_ensure_first_time_calls_fetch(self):
        station = self.create_station()

        with patch("api.services.xema_sync._fetch_and_save") as mock_fetch:
            with patch("api.services.xema_sync._cleanup_old_readings"):
                result = ensure_station_synced(station)

        assert result is True
        mock_fetch.assert_called_once()

    def test_ensure_recent_skips(self):
        station = self.create_station()

        WeatherReading.objects.create(
            station=station,
            timestamp=timezone.now(),
        )

        result = ensure_station_synced(station)

        assert result is False

    def test_cleanup_deletes_old(self):
        station = self.create_station()

        old = timezone.now() - timedelta(days=40)

        WeatherReading.objects.create(
            station=station,
            timestamp=old,
        )

        _cleanup_old_readings(station)

        assert WeatherReading.objects.count() == 0
