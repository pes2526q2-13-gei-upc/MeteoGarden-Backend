from unittest.mock import patch

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from api.models import Station, WeatherReading


@pytest.mark.django_db
class TestViewsXema:

    def setup_method(self):
        self.client = APIClient()

    def create_station(self):
        return Station.objects.create(
            stationCode="1234",
            station="Test Station",
            city="City",
            solarIrradiance=0,
            temperature=0,
            windSpeed=0,
            relativeHumidity=0,
            precipitation=0,
        )

    def test_missing_params(self):
        res = self.client.get("/api/weather/current/")

        assert res.status_code == 400

    def test_station_not_found(self):
        res = self.client.get("/api/weather/current/?stationCode=9999")

        assert res.status_code == 404

    @patch("api.views.views_xema.ensure_station_synced")
    def test_no_readings(self, mock_sync):
        self.create_station()

        res = self.client.get("/api/weather/current/?stationCode=1234")

        assert res.status_code == 503

    @patch("api.views.views_xema.ensure_station_synced")
    def test_success(self, mock_sync):
        station = self.create_station()

        WeatherReading.objects.create(
            station=station,
            timestamp=timezone.now(),
            temperature=25,
            precipitation=0.5,
            windSpeed=10,
        )

        res = self.client.get("/api/weather/current/?stationCode=1234")

        assert res.status_code == 200
        assert res.data["temperature"] == 25
        assert res.data["wind"] == 10

    def test_get_stations_cached(self):
        self.create_station()

        res = self.client.get("/api/stations/")

        assert res.status_code == 200
        assert len(res.data) == 1

    @patch("api.views.views_xema.requests.get")
    def test_get_stations_first_time(self, mock_get):
        mock_get.return_value.json.return_value = [
            {
                "nom_estacio": "Station A",
                "codi_estacio": "1111",
                "municipi": "City A",
            }
        ]

        res = self.client.get("/api/stations/")

        assert res.status_code == 200
        assert Station.objects.count() == 1

    @patch("api.views.views_xema.requests.get")
    def test_get_stations_invalid_response(self, mock_get):
        mock_get.return_value.json.return_value = {"error": "bad"}

        res = self.client.get("/api/stations/")

        assert res.status_code == 500

    @patch("api.views.views_xema.requests.get")
    def test_get_stations_exception(self, mock_get):
        mock_get.side_effect = Exception("boom")

        res = self.client.get("/api/stations/")

        assert res.status_code == 500

    @patch("api.views.views_xema.requests.get")
    def test_get_stations_empty_response(self, mock_get):
        mock_get.return_value.json.return_value = []

        res = self.client.get("/api/stations/")

        assert res.status_code == 200
        assert res.data == []

    @patch("api.views.views_xema.ensure_station_synced")
    def test_latest_reading_used(self, mock_sync):
        station = self.create_station()

        WeatherReading.objects.create(
            station=station,
            timestamp=timezone.now() - timezone.timedelta(hours=1),
            temperature=10,
            windSpeed=5,
        )

        WeatherReading.objects.create(
            station=station,
            timestamp=timezone.now(),
            temperature=30,
            windSpeed=20,
        )

        res = self.client.get("/api/weather/current/?stationCode=1234")

        assert res.status_code == 200
        assert res.data["temperature"] == 30
        assert res.data["wind"] == 20
