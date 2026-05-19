from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from api.models import (
    AlbumEntry,
    Inventory,
    Mission,
    MissionState,
    Plant,
    User,
    UserMission,
)


class MissionTests(APITestCase):

    def setUp(self):

        test_cred = "p4ss_test_123"

        self.user = User.objects.create_user(
            username="tester",
            password=test_cred,
            email="t@t.com",
            city="BCN",
            language="es",
            stationCode="ST01",
        )

        from rest_framework.authtoken.models import Token

        self.token = Token.objects.create(user=self.user)

        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token.key)

        self.plant = Plant.objects.create(
            scientificName="rosa_canina",
            commonName="Rosa Canina",
            family="Rosaceae",
            canFlower=True,
            minTemperature=5.0,
            maxTemperature=35.0,
            description="Una rosa muy bonita",
        )

        self.inventory = Inventory.objects.create(user=self.user, coins=10)

        self.create_url = reverse("createMission")
        self.assign_url = reverse("assignMission")
        self.claim_url = reverse("claimReward")
        self.get_user_missions_url = reverse("getUserMissions")
        self.get_all_missions_url = reverse("getMissions")

    ##################################
    # CREATE MISSION
    ##################################

    def test_create_mission_success(self):

        data = {
            "name": "Misión Rosa",
            "description": "Planta rosas",
            "action": "PLANT",
            "goal": 3,
            "plant": "rosa_canina",
            "rewardCoins": 100,
        }

        response = self.client.post(self.create_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertTrue(Mission.objects.filter(name="Misión Rosa").exists())

    def test_create_mission_missing_fields(self):

        response = self.client.post(self.create_url, {"name": "rota"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_mission_invalid_action(self):

        response = self.client.post(
            self.create_url,
            {"name": "rara", "description": "aaa", "action": "VOLAR"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_mission_plant_not_exists(self):

        response = self.client.post(
            self.create_url,
            {
                "name": "Mision",
                "description": "Desc",
                "action": "PLANT",
                "plant": "inventada",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    ##################################
    # ASSIGN
    ##################################

    def test_assign_mission_to_user(self):

        mission = Mission.objects.create(
            name="Test Mission",
            description="Desc",
            action="WATER",
            goal=1,
            rewardCoins=50,
        )

        response = self.client.post(
            self.assign_url,
            {"mission": "Test Mission", "user": "tester"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertTrue(
            UserMission.objects.filter(user=self.user, mission=mission).exists()
        )

    def test_assign_mission_not_exists(self):

        response = self.client.post(
            self.assign_url, {"mission": "fantasma", "user": "tester"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_assign_user_not_exists(self):

        Mission.objects.create(
            name="Mission", description="Desc", action="PLANT", goal=1, rewardCoins=10
        )

        response = self.client.post(
            self.assign_url, {"mission": "Mission", "user": "fantasma"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    ##################################
    # CLAIM
    ##################################

    def test_claim_reward_success(self):

        mission = Mission.objects.create(
            name="Misión Fácil",
            description="Desc",
            action="PLANT",
            goal=1,
            rewardCoins=100,
        )

        user_mission = UserMission.objects.create(
            user=self.user,
            mission=mission,
            current=1,
            missionState=MissionState.COMPLETED,
            acquiredAt=timezone.now(),
        )

        response = self.client.post(
            self.claim_url, {"mission": "Misión Fácil"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.inventory.refresh_from_db()

        self.assertEqual(self.inventory.coins, 110)

        user_mission.refresh_from_db()

        self.assertEqual(user_mission.missionState, MissionState.CLAIMED)

    def test_claim_reward_in_progress_fails(self):

        mission = Mission.objects.create(
            name="Misión Larga", action="WATER", goal=10, rewardCoins=10
        )

        UserMission.objects.create(
            user=self.user,
            mission=mission,
            current=0,
            missionState=MissionState.IN_PROGRESS,
            acquiredAt=timezone.now(),
        )

        response = self.client.post(
            self.claim_url, {"mission": "Misión Larga"}, format="json"
        )

        self.assertEqual(response.data["error"], "Mission in progress")

    def test_claim_reward_already_claimed(self):

        mission = Mission.objects.create(
            name="Acabada", action="PLANT", goal=1, rewardCoins=20
        )

        UserMission.objects.create(
            user=self.user,
            mission=mission,
            current=1,
            missionState=MissionState.CLAIMED,
            acquiredAt=timezone.now(),
        )

        response = self.client.post(
            self.claim_url, {"mission": "Acabada"}, format="json"
        )

        self.assertEqual(response.data["error"], "Mission already claimed")

    def test_claim_reward_with_plant_reward(self):

        reward_plant = Plant.objects.create(
            scientificName="tulipan",
            commonName="Tulipan",
            family="Rosaceae",
            canFlower=True,
            minTemperature=5,
            maxTemperature=30,
            description="desc",
        )

        mission = Mission.objects.create(
            name="Planta",
            description="Desc",
            action="PLANT",
            goal=1,
            plantReward=reward_plant,
        )

        UserMission.objects.create(
            user=self.user,
            mission=mission,
            current=1,
            missionState=MissionState.COMPLETED,
            acquiredAt=timezone.now(),
        )

        self.client.post(self.claim_url, {"mission": "Planta"}, format="json")

        self.assertTrue(
            AlbumEntry.objects.filter(user=self.user, plant=reward_plant).exists()
        )

    ##################################
    # GET
    ##################################

    def test_get_user_missions(self):

        mission = Mission.objects.create(
            name="M1", description="Desc", action="PLANT", goal=2, rewardCoins=50
        )

        UserMission.objects.create(
            user=self.user,
            mission=mission,
            current=1,
            missionState=MissionState.IN_PROGRESS,
            acquiredAt=timezone.now(),
        )

        response = self.client.get(self.get_user_missions_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(response.data["missions"]), 1)

    def test_get_all_missions(self):

        Mission.objects.create(name="M2", description="Desc", action="PLANT", goal=1)

        response = self.client.get(self.get_all_missions_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(response.data["missions"]), 1)
