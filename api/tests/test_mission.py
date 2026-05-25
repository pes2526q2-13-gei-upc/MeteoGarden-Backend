from unittest.mock import patch

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
    Product,
    User,
    UserMission,
)


def fake_translate(texts, lang):
    if isinstance(texts, list):
        return texts
    return texts


class MissionTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="tester",
            password="p4ss_test_123",
            email="tester@test.com",
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
            minTemperature=5,
            maxTemperature=35,
            description="Una rosa",
        )

        self.reward_plant = Plant.objects.create(
            scientificName="tulipa",
            commonName="Tulipa",
            family="Liliaceae",
            canFlower=True,
            minTemperature=5,
            maxTemperature=30,
            description="Una tulipa",
        )

        self.product = Product.objects.create(
            name="Potion",
            description="Growth potion",
            effectType="growth",
            value=1,
            durationHours=1,
            isInstant=True,
            price=5,
            rarity="common",
        )

        self.reward_product = Product.objects.create(
            name="Reward Potion",
            description="Reward potion",
            effectType="health",
            value=1,
            durationHours=1,
            isInstant=True,
            price=10,
            rarity="common",
        )

        self.inventory = Inventory.objects.create(user=self.user, coins=10)

        self.create_url = reverse("createMission")
        self.assign_url = reverse("assignMission")
        self.claim_url = reverse("claimReward")
        self.get_user_missions_url = reverse("getUserMissions")
        self.get_all_missions_url = reverse("getMissions")

    # CREATE MISSION

    def test_create_mission_success_with_all_rewards(self):
        data = {
            "name": "Full mission",
            "description": "Do everything",
            "action": "PLANT",
            "goal": 3,
            "plant": self.plant.scientificName,
            "product": self.product.name,
            "plant_reward": self.reward_plant.scientificName,
            "rewardCoins": 100,
            "product_reward": self.reward_product.name,
        }

        response = self.client.post(self.create_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mission = Mission.objects.get(name="Full mission")
        self.assertEqual(mission.plant, self.plant)
        self.assertEqual(mission.product, self.product)
        self.assertEqual(mission.plantReward, self.reward_plant)
        self.assertEqual(mission.productReward, self.reward_product)
        self.assertEqual(mission.rewardCoins, 100)

    def test_create_mission_missing_required_fields(self):
        response = self.client.post(
            self.create_url,
            {"name": "Incomplete"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["error"],
            "name, description and action are required fields",
        )

    def test_create_mission_invalid_action(self):
        response = self.client.post(
            self.create_url,
            {
                "name": "Invalid action",
                "description": "Desc",
                "action": "FLY",
                "rewardCoins": 0,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_mission_plant_not_exists(self):
        response = self.client.post(
            self.create_url,
            {
                "name": "Bad plant",
                "description": "Desc",
                "action": "PLANT",
                "plant": "unknown_plant",
                "rewardCoins": 0,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_mission_plant_reward_not_exists(self):
        response = self.client.post(
            self.create_url,
            {
                "name": "Bad reward plant",
                "description": "Desc",
                "action": "PLANT",
                "plant_reward": "unknown_reward",
                "rewardCoins": 0,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_mission_product_not_exists(self):
        response = self.client.post(
            self.create_url,
            {
                "name": "Bad product",
                "description": "Desc",
                "action": "USE",
                "product": "unknown_product",
                "rewardCoins": 0,
            },
            format="json",
        )

        self.assertIn("error", response.data)

    def test_create_mission_product_reward_not_exists(self):
        response = self.client.post(
            self.create_url,
            {
                "name": "Bad reward product",
                "description": "Desc",
                "action": "PLANT",
                "product_reward": "unknown_reward_product",
                "rewardCoins": 0,
            },
            format="json",
        )

        self.assertIn("error", response.data)

    # ASSIGN MISSION

    def test_assign_mission_to_user_success(self):
        mission = Mission.objects.create(
            name="Water mission",
            description="Water",
            action="WATER",
            goal=1,
            rewardCoins=20,
        )

        response = self.client.post(
            self.assign_url,
            {"mission": mission.name, "user": self.user.username},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            UserMission.objects.filter(user=self.user, mission=mission).exists()
        )

    def test_assign_mission_not_exists(self):
        response = self.client.post(
            self.assign_url,
            {"mission": "ghost", "user": self.user.username},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Mission does not exist")

    def test_assign_user_not_exists(self):
        mission = Mission.objects.create(
            name="Mission",
            description="Desc",
            action="PLANT",
            goal=1,
            rewardCoins=10,
        )

        response = self.client.post(
            self.assign_url,
            {"mission": mission.name, "user": "ghost_user"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "User does not exist")

    # CLAIM REWARD

    @patch("api.views.views_missions.translate_text", side_effect=fake_translate)
    def test_claim_reward_success_with_coins_product_and_plant(self, _):
        mission = Mission.objects.create(
            name="Complete mission",
            description="Desc",
            action="PLANT",
            goal=1,
            rewardCoins=100,
            productReward=self.reward_product,
            plantReward=self.reward_plant,
        )

        user_mission = UserMission.objects.create(
            user=self.user,
            mission=mission,
            current=1,
            missionState=MissionState.COMPLETED,
            acquiredAt=timezone.now(),
        )

        response = self.client.post(
            self.claim_url,
            {"mission": mission.name},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.inventory.refresh_from_db()
        user_mission.refresh_from_db()

        self.assertEqual(self.inventory.coins, 110)
        self.assertEqual(user_mission.missionState, MissionState.CLAIMED)
        self.assertTrue(
            AlbumEntry.objects.filter(user=self.user, plant=self.reward_plant).exists()
        )
        self.assertEqual(self.inventory.products[self.reward_product.name], 1)
        self.assertEqual(self.inventory.seeds[self.reward_plant.scientificName], 1)

    @patch("api.views.views_missions.translate_text", side_effect=fake_translate)
    def test_claim_reward_in_progress_fails(self, _):
        mission = Mission.objects.create(
            name="In progress mission",
            description="Desc",
            action="WATER",
            goal=10,
            rewardCoins=10,
        )

        UserMission.objects.create(
            user=self.user,
            mission=mission,
            current=0,
            missionState=MissionState.IN_PROGRESS,
            acquiredAt=timezone.now(),
        )

        response = self.client.post(
            self.claim_url,
            {"mission": mission.name},
            format="json",
        )

        self.assertEqual(response.data["error"], "Mission in progress")

    @patch("api.views.views_missions.translate_text", side_effect=fake_translate)
    def test_claim_reward_already_claimed_fails(self, _):
        mission = Mission.objects.create(
            name="Claimed mission",
            description="Desc",
            action="PLANT",
            goal=1,
            rewardCoins=20,
        )

        UserMission.objects.create(
            user=self.user,
            mission=mission,
            current=1,
            missionState=MissionState.CLAIMED,
            acquiredAt=timezone.now(),
        )

        response = self.client.post(
            self.claim_url,
            {"mission": mission.name},
            format="json",
        )

        self.assertEqual(response.data["error"], "Mission already claimed")

    @patch("api.views.views_missions.translate_text", side_effect=fake_translate)
    def test_claim_reward_does_not_duplicate_album_entry(self, _):
        AlbumEntry.objects.create(
            user=self.user,
            plant=self.reward_plant,
            description="Already unlocked",
        )

        mission = Mission.objects.create(
            name="Plant reward mission",
            description="Desc",
            action="PLANT",
            goal=1,
            plantReward=self.reward_plant,
            rewardCoins=0,
        )

        UserMission.objects.create(
            user=self.user,
            mission=mission,
            current=1,
            missionState=MissionState.COMPLETED,
            acquiredAt=timezone.now(),
        )

        self.client.post(self.claim_url, {"mission": mission.name}, format="json")

        self.assertEqual(
            AlbumEntry.objects.filter(user=self.user, plant=self.reward_plant).count(),
            1,
        )

    # GET MISSIONS

    @patch("api.views.views_missions.translate_text", side_effect=fake_translate)
    def test_get_user_missions_returns_translated_fields(self, _):
        mission = Mission.objects.create(
            name="Mission with relations",
            description="Desc",
            action="USE",
            goal=2,
            plant=self.plant,
            product=self.product,
            plantReward=self.reward_plant,
            productReward=self.reward_product,
            rewardCoins=50,
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

        mission_data = response.data["missions"][0]
        self.assertEqual(mission_data["Name"], mission.name)
        self.assertEqual(mission_data["displayName"], mission.name)
        self.assertEqual(mission_data["Description"], mission.description)
        self.assertEqual(
            mission_data["Plant needed scientific name"], self.plant.scientificName
        )
        self.assertEqual(mission_data["Product needed"], self.product.name)
        self.assertEqual(
            mission_data["Plant reward common name"], self.reward_plant.commonName
        )
        self.assertEqual(
            mission_data["Plant reward scientific name"],
            self.reward_plant.scientificName,
        )
        self.assertEqual(mission_data["Product reward"], self.reward_product.name)

    def test_get_all_missions(self):
        Mission.objects.create(
            name="Public mission",
            description="Desc",
            action="PLANT",
            goal=1,
            rewardCoins=25,
        )

        response = self.client.get(self.get_all_missions_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["missions"]), 1)
        self.assertEqual(response.data["missions"][0]["name"], "Public mission")