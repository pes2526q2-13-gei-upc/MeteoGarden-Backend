from datetime import timedelta
from unittest.mock import patch

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

        assert fields["temperature"] == pytest.approx(20)
        assert fields["precipitation"] == pytest.approx(1)
        assert fields["relativeHumidity"] == pytest.approx(60)
        assert fields["windSpeed"] == pytest.approx(5)

    def test_build_fields_no_wind(self):
        fields = _build_fields({})

        assert "windSpeed" not in fields

    def test_build_fields_wind_fallback(self):
        fields = _build_fields({"48": 7})

        assert fields["windSpeed"] == pytest.approx(7)

    @patch("api.services.xema_sync.requests.get")
    def test_fetch_invalid_response(self, mock_get):
        station = self.create_station()

        mock_get.return_value.json.return_value = {"error": "bad"}

        result = _fetch_and_save(
            station,
            timezone.now() - timedelta(hours=1),
            timezone.now(),
        )

        assert result == 0

    @patch("api.services.xema_sync.requests.get")
    def test_fetch_exception(self, mock_get):
        station = self.create_station()

        mock_get.side_effect = Exception("boom")

        result = _fetch_and_save(
            station,
            timezone.now() - timedelta(hours=1),
            timezone.now(),
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
            station,
            timezone.now() - timedelta(hours=1),
            timezone.now(),
        )

        assert result == 0

    @patch("api.services.xema_sync.requests.get")
    def test_fetch_invalid_float(self, mock_get):
        station = self.create_station()

        mock_get.return_value.json.return_value = [
            {
                "data_lectura": "2025-01-01T12:00:00",
                "codi_variable": "32",
                "valor_lectura": "abc",
            }
        ]

        result = _fetch_and_save(
            station,
            timezone.now() - timedelta(hours=1),
            timezone.now(),
        )

        assert result == 0
        assert WeatherReading.objects.count() == 0

    @patch("api.services.xema_sync.requests.get")
    def test_fetch_invalid_timestamp(self, mock_get):
        station = self.create_station()

        mock_get.return_value.json.return_value = [
            {
                "data_lectura": "invalid-date",
                "codi_variable": "32",
                "valor_lectura": "22",
            }
        ]

        result = _fetch_and_save(
            station,
            timezone.now() - timedelta(hours=1),
            timezone.now(),
        )

        assert result == 0
        assert WeatherReading.objects.count() == 0

    @patch("api.services.xema_sync.requests.get")
    def test_fetch_saves_reading(self, mock_get):
        station = self.create_station()

        mock_get.return_value.json.return_value = [
            {
                "data_lectura": "2025-01-01T12:00:00",
                "codi_variable": "32",
                "valor_lectura": "22",
            },
            {
                "data_lectura": "2025-01-01T12:00:00",
                "codi_variable": "35",
                "valor_lectura": "1.5",
            },
            {
                "data_lectura": "2025-01-01T12:00:00",
                "codi_variable": "46",
                "valor_lectura": "10",
            },
        ]

        result = _fetch_and_save(
            station,
            timezone.now() - timedelta(hours=1),
            timezone.now(),
        )

        assert result == 1
        assert WeatherReading.objects.count() == 1

        reading = WeatherReading.objects.first()

        assert reading.temperature == pytest.approx(22)
        assert reading.precipitation == pytest.approx(1.5)
        assert reading.windSpeed == pytest.approx(10)

    @patch("api.services.xema_sync.requests.get")
    def test_fetch_updates_existing_reading(self, mock_get):
        station = self.create_station()

        timestamp = timezone.now()

        WeatherReading.objects.create(
            station=station,
            timestamp=timestamp,
            temperature=10,
        )

        mock_get.return_value.json.return_value = [
            {
                "data_lectura": timestamp.isoformat(),
                "codi_variable": "32",
                "valor_lectura": "25",
            }
        ]

        result = _fetch_and_save(
            station,
            timestamp - timedelta(hours=1),
            timestamp + timedelta(hours=1),
        )

        assert result == 0
        assert WeatherReading.objects.count() == 1

        reading = WeatherReading.objects.first()

        assert reading.temperature == pytest.approx(25)

    def test_ensure_first_time_calls_fetch(self):
        station = self.create_station()

        with patch("api.services.xema_sync._fetch_and_save") as mock_fetch:
            with patch("api.services.xema_sync._cleanup_old_readings"):
                result = ensure_station_synced(station)

        assert result is True
        mock_fetch.assert_called_once()

    @patch("api.services.xema_sync._fetch_and_save")
    @patch("api.services.xema_sync._cleanup_old_readings")
    def test_ensure_fetches_and_cleans(
        self,
        mock_cleanup,
        mock_fetch,
    ):
        station = self.create_station()

        mock_fetch.return_value = 3

        result = ensure_station_synced(station)

        assert result is True

        mock_fetch.assert_called_once()
        mock_cleanup.assert_called_once()

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

    @patch("api.services.xema_sync.logger.debug")
    def test_cleanup_logs_deleted(self, mock_debug):
        station = self.create_station()

        WeatherReading.objects.create(
            station=station,
            timestamp=timezone.now() - timedelta(days=40),
        )

        _cleanup_old_readings(station)

        mock_debug.assert_called_once()
