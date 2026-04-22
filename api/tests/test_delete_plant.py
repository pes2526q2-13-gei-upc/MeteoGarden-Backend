from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from api.models import Garden, GrowthState, Plant, PlantInGarden, Pot, User


class DeletePlantEndpointTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="pass1234",
            city="Barcelona",
            stationCode="0001",
        )

        self.garden = Garden.objects.create(
            user=self.user,
            name="Mi jardin",
        )

        self.plant = Plant.objects.create(
            scientificName="Rosa canina",
            commonName="Rosal silvestre",
            minTemperature=5.0,
            maxTemperature=35.0,
        )

        self.pot = Pot.objects.create(
            garden=self.garden,
            number=1,
            occupied=False,
        )

        self.url = reverse(
            "delete_plant",
            kwargs={
                "username": self.user.username,
                "garden_name": self.garden.name,
                "pot_number": self.pot.number,
            },
        )

    def test_delete_plant_successfully(self):
        planting = PlantInGarden.objects.create(
            pot=self.pot,
            plant=self.plant,
            plantedAt=timezone.now(),
            growthPhase=GrowthState.SEED,
            healthLevel=100.0,
            waterLevel=100.0,
            lastWateredAt=timezone.now(),
        )

        self.pot.refresh_from_db()
        self.assertTrue(self.pot.occupied)
        self.assertEqual(PlantInGarden.objects.count(), 1)

        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            response.content,
            {
                "message": "Plant deleted successfully.",
                "pot_number": 1,
                "deletedPlant": "Rosa canina",
                "occupied": False,
            },
        )

        self.assertFalse(PlantInGarden.objects.filter(pk=planting.pk).exists())

        self.pot.refresh_from_db()
        self.assertFalse(self.pot.occupied)

    def test_delete_plant_when_pot_is_empty_returns_404(self):
        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, 404)
        self.assertJSONEqual(
            response.content,
            {"error": "There is no plant in this pot."},
        )

    def test_delete_plant_with_get_method_returns_405(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 405)

    def test_delete_plant_with_post_method_returns_405(self):
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 405)

    def test_delete_plant_user_not_found_returns_404(self):
        url = reverse(
            "delete_plant",
            kwargs={
                "username": "unknown_user",
                "garden_name": self.garden.name,
                "pot_number": self.pot.number,
            },
        )

        response = self.client.delete(url)

        self.assertEqual(response.status_code, 404)

    def test_delete_plant_garden_not_found_returns_404(self):
        url = reverse(
            "delete_plant",
            kwargs={
                "username": self.user.username,
                "garden_name": "UnknownGarden",
                "pot_number": self.pot.number,
            },
        )

        response = self.client.delete(url)

        self.assertEqual(response.status_code, 404)

    def test_delete_plant_pot_not_found_returns_404(self):
        url = reverse(
            "delete_plant",
            kwargs={
                "username": self.user.username,
                "garden_name": self.garden.name,
                "pot_number": 99,
            },
        )

        response = self.client.delete(url)

        self.assertEqual(response.status_code, 404)
