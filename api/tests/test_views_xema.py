from unittest.mock import patch

from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from api.models import Station, WeatherReading, User


@override_settings(MEDIA_URL="/media/")
class XemaViewsTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="alice",
            password="test123"
        )

        self.client.force_authenticate(user=self.user)

    def create_station(self):
        return Station.objects.create(
            stationCode="1234",
            station="Test Station",
            city="Barcelona",
            solarIrradiance=0,
            temperature=0,
            windSpeed=0,
            relativeHumidity=0,
            precipitation=0,
        )

    # =========================
    # current_weather
    # =========================

    def test_current_weather_requires_station_param(self):
        url = reverse("current_weather")

        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            res.json(),
            {"error": "stationCode or stationName is required"},
        )

    def test_current_weather_station_not_found(self):
        url = reverse("current_weather")

        res = self.client.get(url, {"stationCode": "9999"})

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(res.json(), {"error": "Station not found"})

    @patch("api.views.views_xema.ensure_station_synced")
    def test_current_weather_no_readings_returns_503(self, mock_sync):
        self.create_station()

        url = reverse("current_weather")

        res = self.client.get(url, {"stationCode": "1234"})

        self.assertEqual(
            res.status_code,
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )

        self.assertEqual(
            res.json(),
            {"error": "No weather data available for this station"},
        )

        mock_sync.assert_called_once()

    @patch("api.views.views_xema.ensure_station_synced")
    def test_current_weather_returns_latest_reading(self, mock_sync):
        station = self.create_station()

        WeatherReading.objects.create(
            station=station,
            timestamp="2025-01-01T10:00:00Z",
            temperature=10,
            precipitation=1,
            windSpeed=5,
            solarIrradiance=100,
            relativeHumidity=50,
        )

        WeatherReading.objects.create(
            station=station,
            timestamp="2025-01-01T11:00:00Z",
            temperature=20,
            precipitation=2,
            windSpeed=10,
            solarIrradiance=200,
            relativeHumidity=60,
        )

        url = reverse("current_weather")

        res = self.client.get(url, {"stationCode": "1234"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        data = res.json()

        self.assertEqual(data["stationName"], "Test Station")
        self.assertEqual(data["temperature"], 20)
        self.assertEqual(data["precipitation"], 2)
        self.assertEqual(data["wind"], 10)
        self.assertEqual(data["solarIrradiance"], 200)
        self.assertEqual(data["relativeHumidity"], 60)

        mock_sync.assert_called_once()

    @patch("api.views.views_xema.ensure_station_synced")
    def test_current_weather_uses_station_name(self, mock_sync):
        station = self.create_station()

        WeatherReading.objects.create(
            station=station,
            timestamp="2025-01-01T12:00:00Z",
            temperature=25,
        )

        url = reverse("current_weather")

        res = self.client.get(
            url,
            {"stationName": "Test Station"},
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertEqual(
            res.json()["temperature"],
            25,
        )

        mock_sync.assert_called_once()

    # =========================
    # get_stations
    # =========================

    def test_get_stations_returns_cached_stations(self):
        self.create_station()

        url = reverse("get_stations")

        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        data = res.json()

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "Test Station")
        self.assertEqual(data[0]["code"], "1234")

    @patch("api.views.views_xema.requests.get")
    def test_get_stations_fetches_from_xema(self, mock_get):
        mock_get.return_value.json.return_value = [
            {
                "nom_estacio": "Station A",
                "codi_estacio": "1111",
                "municipi": "City A",
            }
        ]

        url = reverse("get_stations")

        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        data = res.json()

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "Station A")
        self.assertEqual(data[0]["code"], "1111")

    @patch("api.views.views_xema.requests.get")
    def test_get_stations_invalid_response_returns_500(self, mock_get):
        mock_get.return_value.json.return_value = {"error": "bad"}

        url = reverse("get_stations")

        res = self.client.get(url)

        self.assertEqual(
            res.status_code,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

        self.assertEqual(
            res.json()["error"],
            "Invalid response from XEMA",
        )

    @patch("api.views.views_xema.requests.get")
    def test_get_stations_exception_returns_500(self, mock_get):
        mock_get.side_effect = Exception("boom")

        url = reverse("get_stations")

        res = self.client.get(url)

        self.assertEqual(
            res.status_code,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

        self.assertEqual(
            res.json(),
            {"error": "boom"},
        )

    @patch("api.views.views_xema.requests.get")
    def test_get_stations_empty_response(self, mock_get):
        mock_get.return_value.json.return_value = []

        url = reverse("get_stations")

        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.json(), [])

    @patch("api.views.views_xema.requests.get")
    def test_get_stations_uses_station_name_as_city_fallback(self, mock_get):
        mock_get.return_value.json.return_value = [
            {
                "nom_estacio": "Station A",
                "codi_estacio": "1111",
            }
        ]

        url = reverse("get_stations")

        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        station = Station.objects.get(stationCode="1111")

        self.assertEqual(station.city, "Station A")
