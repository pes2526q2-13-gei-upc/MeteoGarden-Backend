from datetime import timedelta
from unittest.mock import patch

from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from api.models import (
    Garden,
    Inventory,
    MissionAction,
    MissionState,
    Plant,
    PlantInGarden,
    Pot,
    Station,
    User,
)


class TestGardenViewsAPI(APITestCase):

    def setUp(self):

        self.client = APIClient()

        self.user = User.objects.create_user(
            username="alice",
            password="123",
            email="a@a.com",
            city="bcn",
            stationCode="0001",
        )
        self.client.force_login(self.user)

        self.garden = Garden.objects.create(user=self.user, name="garden")

        self.pot = Pot.objects.create(garden=self.garden, number=1)

        self.plant = Plant.objects.create(
            scientificName="Rose",
            commonName="Rose",
            minTemperature=5,
            maxTemperature=30,
        )

    ################################
    # gardens
    ################################

    def test_user_gardens(self):

        url = reverse("user_gardens", args=["alice"])

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        self.assertEqual(response.json()[0]["name"], "garden")

    ################################
    # seeds
    ################################

    def test_user_seeds(self):

        inventory, _ = Inventory.objects.get_or_create(user=self.user)

        inventory.seeds = {"Rose": 5}

        inventory.save()

        url = reverse("user_seeds", args=["alice"])

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        self.assertEqual(response.json()[0]["scientificName"], "Rose")

    ################################
    # products
    ################################

    def test_user_products(self):

        inventory, _ = Inventory.objects.get_or_create(user=self.user)

        inventory.products = {"heal": 2}

        inventory.save()

        url = reverse("user_products", args=["alice"])

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

    ################################
    # water
    ################################

    def test_water_wrong_method(self):

        url = reverse("water_plant", args=["alice", "garden", 1])

        response = self.client.get(url)

        self.assertEqual(response.status_code, 405)

    def test_water_empty_pot(self):

        url = reverse("water_plant", args=["alice", "garden", 1])

        response = self.client.patch(url)

        self.assertEqual(response.status_code, 404)

    def test_water_recently(self):

        PlantInGarden.objects.create(
            pot=self.pot,
            plant=self.plant,
            healthLevel=50,
            waterLevel=50,
            lastWateredAt=timezone.now(),
        )

        url = reverse("water_plant", args=["alice", "garden", 1])

        response = self.client.patch(url)

        self.assertEqual(response.status_code, 400)

    ################################
    # plant status
    ################################

    @patch("api.views.views_visualitzarJardi.simulate_plant")
    @patch("api.views.views_visualitzarJardi.ensure_station_synced")
    def test_plant_status(self, mock_sync, mock_sim):

        Station.objects.create(
            stationCode="0001",
            station="s",
            city="bcn",
            solarIrradiance=1,
            temperature=20,
            windSpeed=1,
            relativeHumidity=1,
            precipitation=1,
        )

        pig = PlantInGarden.objects.create(
            pot=self.pot, plant=self.plant, healthLevel=50, waterLevel=50
        )

        mock_sim.return_value = pig

        url = reverse("plant_status", args=["alice", "garden", 1])

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

    ################################
    # simulate garden
    ################################

    @patch("api.views.views_visualitzarJardi.simulate_plant")
    @patch("api.views.views_visualitzarJardi.ensure_station_synced")
    def test_garden_plants(self, mock_sync, mock_sim):

        Station.objects.create(
            stationCode="0001",
            station="station",
            city="bcn",
            solarIrradiance=1,
            temperature=20,
            windSpeed=1,
            relativeHumidity=1,
            precipitation=1,
        )

        pig = PlantInGarden.objects.create(
            pot=self.pot, plant=self.plant, healthLevel=50, waterLevel=50
        )

        mock_sim.return_value = pig

        url = reverse("garden-plants", args=["alice", "garden"])

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

    ################################
    # simulate no station
    ################################

    def test_garden_without_station(self):

        url = reverse("garden-plants", args=["alice", "garden"])

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

    ################################
    # invalid methods
    ################################

    def test_user_seeds_invalid(self):

        url = reverse("user_seeds", args=["alice"])

        response = self.client.post(url)

        self.assertEqual(response.status_code, 405)

    def test_user_products_invalid(self):

        url = reverse("user_products", args=["alice"])

        response = self.client.post(url)

        self.assertEqual(response.status_code, 405)

    def test_water_successfully(self):
        planting = PlantInGarden.objects.create(
            pot=self.pot,
            plant=self.plant,
            healthLevel=50,
            waterLevel=40,
            lastWateredAt=timezone.now() - timedelta(hours=11),
        )

        url = reverse("water_plant", args=["alice", "garden", 1])

        response = self.client.patch(url)

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertEqual(data["message"], "Plant watered successfully.")
        self.assertEqual(data["pot_number"], 1)
        self.assertEqual(data["plant"]["scientific_name"], "Rose")
        self.assertEqual(data["plant"]["common_name"], "Rose")
        self.assertEqual(data["water_level"], 100.0)
        self.assertEqual(data["health_level"], 55.0)
        self.assertIn("last_watered_at", data)

        planting.refresh_from_db()

        self.assertEqual(planting.waterLevel, 100.0)
        self.assertEqual(planting.healthLevel, 55.0)