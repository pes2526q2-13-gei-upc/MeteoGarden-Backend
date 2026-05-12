from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from api.models import (
    Inventory,
    Mission,
    MissionAction,
    MissionState,
    Plant,
    User,
    UserMission,
)


class MissionTests(APITestCase):

    def setUp(self):
        # 1. Crear usuario y autenticarlo
        test_cred = "p4ss_test_123"  # Cambiamos el nombre de la variable
        self.user = User.objects.create_user(
            username="tester",
            password=test_cred,  # Pasamos la variable
            email="t@t.com",
            city="BCN",
            language="es",
            stationCode="ST01",
        )
        from rest_framework.authtoken.models import Token

        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token.key)

        # 2. Crear objetos necesarios para las misiones
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

        # 3. URLs
        self.create_url = reverse("createMission")
        self.assign_url = reverse("assignMission")
        self.claim_url = reverse("claimReward")
        self.get_user_missions_url = reverse("getUserMissions")

    def test_create_mission_success(self):
        """Prueba crear una misión básica"""
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

    def test_assign_mission_to_user(self):
        """Prueba asignar una misión existente a un usuario"""
        mission = Mission.objects.create(
            name="Test Mission",
            description="Desc",
            action="WATER",
            goal=1,
            rewardCoins=50,
        )
        data = {"mission": "Test Mission", "user": "tester"}
        response = self.client.post(self.assign_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            UserMission.objects.filter(user=self.user, mission=mission).exists()
        )

    def test_claim_reward_success(self):
        """Prueba reclamar premio de una misión completada"""
        # Crear misión y asignarla como COMPLETED
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
            missionState=MissionState.COMPLETED,  # Forzamos completada
            acquiredAt=timezone.now(),
        )

        data = {"mission": "Misión Fácil"}
        response = self.client.post(self.claim_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verificar que las monedas subieron en el inventario
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.coins, 110)  # 10 iniciales + 100 premio

        # Verificar que el estado cambió a CLAIMED
        user_mission.refresh_from_db()
        self.assertEqual(user_mission.missionState, MissionState.CLAIMED)

    def test_claim_reward_in_progress_fails(self):
        """No se puede reclamar una misión que está IN_PROGRESS"""
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

        data = {"mission": "Misión Larga"}
        response = self.client.post(self.claim_url, data, format="json")

        self.assertEqual(
            response.status_code, status.HTTP_200_OK
        )  # Tu vista devuelve 200 con error en el body
        self.assertEqual(response.data["error"], "Mission in progress")
