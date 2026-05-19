from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from api.models import (
    AlbumEntry,
    Garden,
    GrowthState,
    Inventory,
    Mission,
    MissionAction,
    MissionState,
    Plant,
    PlantInGarden,
    Pot,
    User,
    UserMission,
)


class CollectPlantTests(APITestCase):

    def setUp(self):

        test_cred = "p4ss_test_123"

        self.user = User.objects.create_user(
            username="tester",
            password=test_cred,
            email="test@test.com",
            city="BCN",
            language="es",
            stationCode="ST01",
        )

        from rest_framework.authtoken.models import Token

        self.token = Token.objects.create(user=self.user)

        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token.key)

        self.inventory = Inventory.objects.create(user=self.user, coins=10)

        self.plant = Plant.objects.create(
            scientificName="rosa_canina",
            commonName="Rosa Canina",
            family="Rosaceae",
            canFlower=True,
            minTemperature=5,
            maxTemperature=35,
            description="Una rosa muy bonita",
        )

        # IMPORTANT:
        # addSeed() requereix que la planta
        # existeixi a l'àlbum

        AlbumEntry.objects.create(user=self.user, plant=self.plant, description="test")

        self.garden = Garden.objects.create(user=self.user, name="Garden1")

        self.pot = Pot.objects.create(garden=self.garden, number=1, occupied=False)

        self.collect_url = reverse(
            "collect_plant",
            kwargs={
                "username": self.user.username,
                "garden_name": self.garden.name,
                "pot_number": self.pot.number,
            },
        )

    def create_plant_in_garden(self, phase=GrowthState.MATURE):

        return PlantInGarden.objects.create(
            pot=self.pot,
            plant=self.plant,
            growthPhase=phase,
            healthLevel=100,
            waterLevel=100,
        )

    ###################################
    # COLLECT
    ###################################

    def test_collect_success(self):

        self.create_plant_in_garden()

        response = self.client.post(
            self.collect_url, {"plant": self.plant.scientificName}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.inventory.refresh_from_db()

        self.assertEqual(self.inventory.coins, 12)

        self.assertFalse(PlantInGarden.objects.filter(pot=self.pot).exists())

        self.pot.refresh_from_db()

        self.assertFalse(self.pot.occupied)

    def test_collect_missing_fields(self):

        response = self.client.post(self.collect_url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_collect_plant_not_found(self):

        response = self.client.post(
            self.collect_url, {"plant": "inventada"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_collect_not_mature(self):

        self.create_plant_in_garden(GrowthState.SEED)

        response = self.client.post(
            self.collect_url, {"plant": self.plant.scientificName}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_collect_completes_collect_mission(self):

        self.create_plant_in_garden()

        mission = Mission.objects.create(
            name="Recolecta Rosa",
            description="Recoge una rosa",
            action=MissionAction.COLLECT,
            goal=1,
        )

        user_mission = UserMission.objects.create(
            user=self.user,
            mission=mission,
            current=0,
            missionState=MissionState.IN_PROGRESS,
            acquiredAt=timezone.now(),
        )

        response = self.client.post(
            self.collect_url, {"plant": self.plant.scientificName}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        user_mission.refresh_from_db()

        self.assertEqual(user_mission.current, 1)

        self.assertEqual(user_mission.missionState, MissionState.COMPLETED)

    def test_collect_wrong_plant_does_not_complete_mission(self):

        another_plant = Plant.objects.create(
            scientificName="tulipan",
            commonName="Tulipan",
            family="Rosaceae",
            canFlower=True,
            minTemperature=5,
            maxTemperature=30,
            description="desc",
        )

        self.create_plant_in_garden()

        mission = Mission.objects.create(
            name="Recolecta Tulipan",
            description="Recoge un tulipan",
            action=MissionAction.COLLECT,
            goal=1,
            plant=another_plant,
        )

        user_mission = UserMission.objects.create(
            user=self.user,
            mission=mission,
            current=0,
            missionState=MissionState.IN_PROGRESS,
            acquiredAt=timezone.now(),
        )

        self.client.post(
            self.collect_url, {"plant": self.plant.scientificName}, format="json"
        )

        user_mission.refresh_from_db()

        self.assertEqual(user_mission.current, 0)

        self.assertEqual(user_mission.missionState, MissionState.IN_PROGRESS)
