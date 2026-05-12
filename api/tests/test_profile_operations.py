from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from api.models import Garden, Inventory, Pot, User


class AuthTests(APITestCase):

    def setUp(self):
        # Datos para registrar un usuario de prueba
        self.register_url = reverse(
            "register"
        )  # Asegúrate de que este sea el 'name' en urls.py
        self.login_url = reverse("login")
        self.profile_url = reverse("get_profile")

        self.user_data = {
            "username": "testuser",
            "password": "testpassword123",
            "email": "test@example.com",
            "city": "Barcelona",
            "language": "es",
            "stationCode": "bc",
            "gardenName": "Mi Jardincito",
        }

    ## --- TESTS DE REGISTRO --- ##

    def test_register_user_success(self):
        """Comprueba que el registro crea usuario, inventario, jardín y macetas"""
        response = self.client.post(self.register_url, self.user_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("token", response.data)

        # Verificar base de datos
        user = User.objects.get(username="testuser")
        self.assertTrue(Inventory.objects.filter(user=user).exists())
        self.assertTrue(Garden.objects.filter(user=user, name="Mi Jardincito").exists())
        self.assertEqual(Pot.objects.filter(garden__user=user).count(), 16)

    def test_register_missing_garden_name(self):
        """Error si no mandas el nombre del jardín"""
        data = self.user_data.copy()
        del data["gardenName"]
        response = self.client.post(self.register_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    ## --- TESTS DE LOGIN --- ##

    def test_login_success(self):
        # Primero registramos
        User.objects.create_user(
            username="testuser", password="testpassword123", email="a@a.com"
        )

        data = {"username": "testuser", "password": "testpassword123"}
        response = self.client.post(self.login_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("token", response.data)

    ## --- TESTS DE PERFIL (REQUIEREN TOKEN) --- ##

    def test_get_profile_authenticated(self):
        # 1. Crear usuario e inventario
        user = User.objects.create_user(
            username="juanjo", password="password", email="j@j.com"
        )
        Inventory.objects.create(user=user)
        Garden.objects.create(user=user, name="Main Garden")

        # 2. Autenticar al cliente con Token
        from rest_framework.authtoken.models import Token

        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION="Token " + token.key)

        # 3. Pedir perfil
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "juanjo")
        self.assertEqual(len(response.data["gardens"]), 1)

    def test_get_profile_unauthenticated(self):
        """Si no mando token, debe dar 401"""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
