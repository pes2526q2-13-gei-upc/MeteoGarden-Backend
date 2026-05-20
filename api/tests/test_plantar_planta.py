import json

from django.urls import reverse
from rest_framework.test import APIClient, APITestCase

from api.models import (
    Garden,
    GrowthState,
    Inventory,
    Plant,
    PlantInGarden,
    Pot,
    User,
)


class TestPlantarPlantaAPI(APITestCase):
    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create_user(
            username="alice",
            password="123",
            email="alice@test.com",
            city="bcn",
            stationCode="0001",
        )
        self.client.force_login(self.user)

        self.garden = Garden.objects.create(
            user=self.user,
            name="garden",
        )

        self.pot = Pot.objects.create(
            garden=self.garden,
            number=1,
        )

        self.plant = Plant.objects.create(
            scientificName="Rose",
            commonName="Rose",
            family="Rosaceae",
            description="A rose plant.",
            minTemperature=5,
            maxTemperature=30,
        )

    def plant_url(self, pot_number=1):
        return reverse("plant_seed", args=["alice", "garden", pot_number])

    def delete_url(self, pot_number=1):
        return reverse("delete_plant", args=["alice", "garden", pot_number])

    ################################
    # plant seed
    ################################

    def test_plant_seed_successfully(self):
        inventory, _ = Inventory.objects.get_or_create(user=self.user)
        inventory.seeds = {"Rose": 2}
        inventory.save()

        response = self.client.post(
            self.plant_url(),
            data=json.dumps({"scientificName": "Rose"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)

        body = response.json()
        self.assertEqual(body["message"], "Plant planted successfully.")
        self.assertEqual(body["pot_number"], 1)
        self.assertEqual(body["plant"]["scientificName"], "Rose")
        self.assertEqual(body["plant"]["commonName"], "Rose")
        self.assertEqual(body["growthPhase"], GrowthState.SEED)
        self.assertEqual(body["healthLevel"], 100.0)
        self.assertEqual(body["waterLevel"], 100.0)
        self.assertEqual(body["remainingSeeds"], 1)

        self.assertTrue(
            PlantInGarden.objects.filter(
                pot=self.pot,
                plant=self.plant,
            ).exists()
        )

        inventory.refresh_from_db()
        self.assertEqual(inventory.seeds["Rose"], 1)

    def test_plant_seed_removes_seed_when_amount_becomes_zero(self):
        inventory, _ = Inventory.objects.get_or_create(user=self.user)
        inventory.seeds = {"Rose": 1}
        inventory.save()

        response = self.client.post(
            self.plant_url(),
            data=json.dumps({"scientificName": "Rose"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)

        inventory.refresh_from_db()
        self.assertNotIn("Rose", inventory.seeds)
        self.assertEqual(response.json()["remainingSeeds"], 0)

    def test_plant_seed_invalid_json(self):
        response = self.client.generic(
            "POST",
            self.plant_url(),
            data="{invalid-json",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Invalid JSON body.")

    def test_plant_seed_missing_scientific_name(self):
        response = self.client.post(
            self.plant_url(),
            data=json.dumps({}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["error"],
            "The field 'scientificName' is required.",
        )

    def test_plant_seed_plant_not_found(self):
        response = self.client.post(
            self.plant_url(),
            data=json.dumps({"scientificName": "UnknownPlant"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 404)

    def test_plant_seed_without_seed_in_inventory(self):
        inventory, _ = Inventory.objects.get_or_create(user=self.user)
        inventory.seeds = {}
        inventory.save()

        response = self.client.post(
            self.plant_url(),
            data=json.dumps({"scientificName": "Rose"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["error"],
            "The user does not have this seed in the inventory.",
        )

    def test_plant_seed_with_zero_amount_in_inventory(self):
        inventory, _ = Inventory.objects.get_or_create(user=self.user)
        inventory.seeds = {"Rose": 0}
        inventory.save()

        response = self.client.post(
            self.plant_url(),
            data=json.dumps({"scientificName": "Rose"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["error"],
            "The user does not have this seed in the inventory.",
        )

    def test_plant_seed_pot_already_occupied(self):
        PlantInGarden.objects.create(
            pot=self.pot,
            plant=self.plant,
            growthPhase=GrowthState.SEED,
            healthLevel=100.0,
            waterLevel=100.0,
        )

        inventory, _ = Inventory.objects.get_or_create(user=self.user)
        inventory.seeds = {"Rose": 1}
        inventory.save()

        response = self.client.post(
            self.plant_url(),
            data=json.dumps({"scientificName": "Rose"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "This pot is already occupied.")

    def test_plant_seed_wrong_method(self):
        response = self.client.get(self.plant_url())

        self.assertEqual(response.status_code, 405)

    ################################
    # delete plant
    ################################

    def test_delete_plant_successfully(self):
        PlantInGarden.objects.create(
            pot=self.pot,
            plant=self.plant,
            growthPhase=GrowthState.SEED,
            healthLevel=100.0,
            waterLevel=100.0,
        )

        response = self.client.delete(self.delete_url())

        self.assertEqual(response.status_code, 200)

        body = response.json()
        self.assertEqual(body["message"], "Plant deleted successfully.")
        self.assertEqual(body["pot_number"], 1)
        self.assertEqual(body["deletedPlant"], "Rose")

        self.assertFalse(
            PlantInGarden.objects.filter(
                pot=self.pot,
                plant=self.plant,
            ).exists()
        )

    def test_delete_plant_empty_pot(self):
        response = self.client.delete(self.delete_url())

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"], "There is no plant in this pot.")

    def test_delete_plant_pot_not_found(self):
        response = self.client.delete(self.delete_url(pot_number=99))

        self.assertEqual(response.status_code, 404)

    def test_delete_plant_wrong_method(self):
        response = self.client.get(self.delete_url())

        self.assertEqual(response.status_code, 405)