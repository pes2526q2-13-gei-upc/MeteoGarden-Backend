from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from api.models import Garden, Inventory, Pot, User


class AuthTests(APITestCase):

    def setUp(self):
        self.register_url = reverse("register")
        self.login_url = reverse("login")
        self.profile_url = reverse("get_profile")
        self.edit_profile_url = reverse("edit_profile")
        self.delete_profile_url = reverse("delete_profile")
        self.validate_token_url = reverse("validate_token")

        self.user_data = {
            "username": "testuser",
            "password": "testpassword123",
            "email": "test@example.com",
            "city": "Barcelona",
            "language": "es",
            "stationCode": "bc",
            "gardenName": "Mi Jardincito",
        }

    ##################################
    # TESTS DE REGISTRO
    ##################################

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
        self.assertIn("error", response.data)

    def test_register_creates_16_pots(self):
        """Verifica que se crean exactamente 16 macetas"""
        response = self.client.post(self.register_url, self.user_data, format="json")
        user = User.objects.get(username="testuser")
        garden = Garden.objects.get(user=user)
        pots = Pot.objects.filter(garden=garden)

        self.assertEqual(pots.count(), 16)
        pot_numbers = sorted([pot.number for pot in pots])
        self.assertEqual(pot_numbers, list(range(1, 17)))

    def test_register_creates_token(self):
        """Verifica que se crea un token de autenticación"""
        response = self.client.post(self.register_url, self.user_data, format="json")
        user = User.objects.get(username="testuser")
        token_exists = Token.objects.filter(user=user).exists()
        self.assertTrue(token_exists)

    ##################################
    # TESTS DE LOGIN
    ##################################

    def test_login_success(self):
        """Login exitoso con credenciales correctas"""
        User.objects.create_user(
            username="testuser",
            password="testpassword123",
            email="test@example.com",
            city="Barcelona",
            language="es",
            stationCode="bc",
        )

        data = {"username": "testuser", "password": "testpassword123"}
        response = self.client.post(self.login_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("token", response.data)
        self.assertEqual(response.data["username"], "testuser")

    def test_login_wrong_password(self):
        """Login falla con contraseña incorrecta"""
        User.objects.create_user(
            username="testuser",
            password="correctpassword",
            email="test@example.com",
            city="Barcelona",
            language="es",
            stationCode="bc",
        )

        response = self.client.post(
            self.login_url,
            {"username": "testuser", "password": "wrongpassword"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Wrong credentials")

    def test_login_nonexistent_user(self):
        """Login falla con usuario que no existe"""
        response = self.client.post(
            self.login_url,
            {"username": "nonexistent", "password": "password"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    ##################################
    # TESTS DE PERFIL - GET
    ##################################

    def test_get_profile_authenticated(self):
        """Obtener perfil con autenticación exitosa"""
        user = User.objects.create_user(
            username="juanjo",
            password="password",
            email="j@j.com",
            city="Barcelona",
            language="es",
            stationCode="bcn",
        )
        Inventory.objects.create(user=user, coins=100)
        Garden.objects.create(user=user, name="Main Garden")

        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION="Token " + token.key)

        response = self.client.get(self.profile_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "juanjo")
        self.assertEqual(response.data["email"], "j@j.com")
        self.assertEqual(response.data["city"], "Barcelona")
        self.assertEqual(response.data["numCoins"], 100)
        self.assertEqual(len(response.data["gardens"]), 1)

    def test_get_profile_multiple_gardens(self):
        """Obtener perfil con múltiples jardines"""
        user = User.objects.create_user(
            username="juanjo", password="password", email="j@j.com"
        )
        Inventory.objects.create(user=user)
        Garden.objects.create(user=user, name="Garden 1")
        Garden.objects.create(user=user, name="Garden 2")
        Garden.objects.create(user=user, name="Garden 3")

        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION="Token " + token.key)

        response = self.client.get(self.profile_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["gardens"]), 3)

    def test_get_profile_unauthenticated(self):
        """Obtener perfil sin token da 401"""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_profile_invalid_token(self):
        """Obtener perfil con token inválido da 401"""
        self.client.credentials(HTTP_AUTHORIZATION="Token invalidtoken")
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    ##################################
    # TESTS DE PERFIL - EDITAR
    ##################################

    def test_edit_profile_success(self):
        """Editar perfil con datos válidos"""
        user = User.objects.create_user(
            username="juan",
            password="1234",
            email="j@j.com",
            city="Old",
            language="es",
            stationCode="BCN",
        )

        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION="Token " + token.key)

        response = self.client.post(
            self.edit_profile_url, {"city": "Madrid", "language": "en"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertEqual(user.city, "Madrid")
        self.assertEqual(user.language, "en")

    def test_edit_profile_email(self):
        """Editar solo el email"""
        user = User.objects.create_user(
            username="juan", password="1234", email="j@j.com"
        )

        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION="Token " + token.key)

        response = self.client.post(
            self.edit_profile_url, {"email": "new@j.com"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertEqual(user.email, "new@j.com")

    def test_edit_profile_num_plants_collected(self):
        """Editar número de plantas coleccionadas"""
        user = User.objects.create_user(
            username="juan", password="1234", email="j@j.com", numPlantsCollected=5
        )

        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION="Token " + token.key)

        response = self.client.post(
            self.edit_profile_url, {"numPlantsCollected": 15}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertEqual(user.numPlantsCollected, 15)

    def test_edit_profile_password_change(self):
        """Cambiar contraseña"""
        user = User.objects.create_user(
            username="juan", password="oldpassword", email="j2@j.com"
        )

        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION="Token " + token.key)

        response = self.client.post(
            self.edit_profile_url, {"password": "newpassword"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertTrue(user.check_password("newpassword"))
        self.assertFalse(user.check_password("oldpassword"))

    def test_edit_profile_multiple_fields(self):
        """Editar múltiples campos a la vez"""
        user = User.objects.create_user(
            username="juan",
            password="1234",
            email="old@j.com",
            city="Barcelona",
            language="es",
        )

        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION="Token " + token.key)

        response = self.client.post(
            self.edit_profile_url,
            {
                "email": "new@j.com",
                "city": "Madrid",
                "language": "ca",
                "numPlantsCollected": 20,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertEqual(user.email, "new@j.com")
        self.assertEqual(user.city, "Madrid")
        self.assertEqual(user.language, "ca")
        self.assertEqual(user.numPlantsCollected, 20)

    def test_edit_profile_unauthenticated(self):
        """Editar perfil sin token da 401"""
        response = self.client.post(
            self.edit_profile_url, {"city": "Madrid"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_edit_profile_preserves_unedited_fields(self):
        """Editar un campo no debe afectar otros"""
        user = User.objects.create_user(
            username="juan",
            password="1234",
            email="j@j.com",
            city="Barcelona",
            language="es",
        )

        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION="Token " + token.key)

        self.client.post(self.edit_profile_url, {"city": "Madrid"}, format="json")

        user.refresh_from_db()
        self.assertEqual(user.city, "Madrid")
        self.assertEqual(user.email, "j@j.com")
        self.assertEqual(user.language, "es")

    ##################################
    # TESTS DE PERFIL - ELIMINAR
    ##################################

    def test_delete_profile_success(self):
        """Eliminar perfil exitosamente"""
        user = User.objects.create_user(
            username="delete_me", password="1234", email="delete@test.com"
        )

        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION="Token " + token.key)

        response = self.client.delete(self.delete_profile_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(User.objects.filter(username="delete_me").exists())

    def test_delete_profile_cascades(self):
        """Eliminar perfil elimina también inventario, jardín y macetas"""
        user = User.objects.create_user(
            username="delete_me", password="1234", email="delete@test.com"
        )
        inventory = Inventory.objects.create(user=user)
        garden = Garden.objects.create(user=user, name="Test Garden")
        Pot.objects.create(garden=garden, number=1)

        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION="Token " + token.key)

        username = user.username
        self.client.delete(self.delete_profile_url)

        self.assertFalse(User.objects.filter(username=username).exists())

        self.assertFalse(Inventory.objects.filter(user__username=username).exists())

        self.assertFalse(Garden.objects.filter(user__username=username).exists())

    def test_delete_profile_unauthenticated(self):
        """Eliminar perfil sin token da 401"""
        response = self.client.delete(self.delete_profile_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    ##################################
    # TESTS DE VALIDAR TOKEN
    ##################################

    def test_validate_token_success(self):
        """Validar token válido"""
        user = User.objects.create_user(
            username="tokenuser", password="1234", email="token@test.com"
        )

        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION="Token " + token.key)

        response = self.client.post(self.validate_token_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["valid"])
        self.assertEqual(response.data["username"], "tokenuser")

    def test_validate_token_without_auth(self):
        """Validar sin token da 401"""
        response = self.client.post(self.validate_token_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_validate_token_invalid_token(self):
        """Validar con token inválido da 401"""
        self.client.credentials(HTTP_AUTHORIZATION="Token invalidtoken")
        response = self.client.post(self.validate_token_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class GoogleAuthTests(APITestCase):

    def setUp(self):
        self.google_verify_url = reverse("google_verify")
        self.google_register_url = reverse("google_register")

    ##################################
    # TESTS DE GOOGLE VERIFY
    ##################################

    def test_google_verify_missing_token(self):
        """Error si no mandas id_token"""
        response = self.client.post(self.google_verify_url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "id_token is required")

    @patch("api.views.views_profile_operations.verify_google_token")
    def test_google_verify_invalid_token(self, mock_verify):
        """Error con token inválido"""
        mock_verify.side_effect = ValueError("Invalid token")

        response = self.client.post(
            self.google_verify_url, {"id_token": "fake"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Invalid Google token")

    @patch("api.views.views_profile_operations.verify_google_token")
    def test_google_verify_existing_user(self, mock_verify):
        """Usuario Google existente retorna exists=True"""
        User.objects.create_user(
            username="googleuser", email="google@test.com", google_id="123"
        )

        mock_verify.return_value = {
            "sub": "123",
            "email": "google@test.com",
            "name": "Google User",
        }

        response = self.client.post(
            self.google_verify_url, {"id_token": "fake"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["exists"])
        self.assertIn("token", response.data)
        self.assertEqual(response.data["username"], "googleuser")

    @patch("api.views.views_profile_operations.verify_google_token")
    def test_google_verify_new_user(self, mock_verify):
        """Usuario Google nuevo retorna exists=False"""
        mock_verify.return_value = {
            "sub": "999",
            "email": "new@test.com",
            "name": "New User",
        }

        response = self.client.post(
            self.google_verify_url, {"id_token": "fake"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["exists"])
        self.assertEqual(response.data["email"], "new@test.com")
        self.assertEqual(response.data["name"], "New User")

    @patch("api.views.views_profile_operations.verify_google_token")
    def test_google_verify_by_email(self, mock_verify):
        """Encontrar usuario existente por email si no por google_id"""
        User.objects.create_user(username="emailuser", email="test@test.com")

        mock_verify.return_value = {
            "sub": "999",
            "email": "test@test.com",
            "name": "Email User",
        }

        response = self.client.post(
            self.google_verify_url, {"id_token": "fake"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["exists"])

    ##################################
    # TESTS DE GOOGLE REGISTER
    ##################################

    @patch("api.views.views_profile_operations.verify_google_token")
    def test_google_register_missing_token(self, mock_verify):
        """Error si no mandas id_token"""
        response = self.client.post(self.google_register_url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "id_token is required")

    @patch("api.views.views_profile_operations.verify_google_token")
    def test_google_register_missing_fields(self, mock_verify):
        """Error si faltan campos requeridos"""
        mock_verify.return_value = {"sub": "555", "email": "g@test.com"}

        response = self.client.post(
            self.google_register_url, {"id_token": "fake"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    @patch("api.views.views_profile_operations.verify_google_token")
    def test_google_register_invalid_token(self, mock_verify):
        """Error con token inválido"""
        mock_verify.side_effect = ValueError("Invalid token")

        response = self.client.post(
            self.google_register_url, {"id_token": "fake"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("api.views.views_profile_operations.verify_google_token")
    def test_google_register_user_already_exists(self, mock_verify):
        """Error si el usuario Google ya existe"""
        User.objects.create_user(
            username="googleuser", email="google@test.com", google_id="123"
        )

        mock_verify.return_value = {"sub": "123", "email": "google@test.com"}

        response = self.client.post(
            self.google_register_url,
            {
                "id_token": "fake",
                "username": "newuser",
                "city": "Barcelona",
                "language": "es",
                "stationCode": "BCN",
                "gardenName": "Garden",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already exists", response.data["error"])

    @patch("api.views.views_profile_operations.verify_google_token")
    def test_google_register_email_already_registered(self, mock_verify):
        """Error si el email ya está registrado"""
        User.objects.create_user(username="otheruser", email="existing@test.com")

        mock_verify.return_value = {"sub": "999", "email": "existing@test.com"}

        response = self.client.post(
            self.google_register_url,
            {
                "id_token": "fake",
                "username": "newuser",
                "city": "Barcelona",
                "language": "es",
                "stationCode": "BCN",
                "gardenName": "Garden",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Email already registered", response.data["error"])

    @patch("api.views.views_profile_operations.verify_google_token")
    def test_google_register_username_already_taken(self, mock_verify):
        """Error si el username ya está en uso"""
        User.objects.create_user(username="takenusername", email="other@test.com")

        mock_verify.return_value = {"sub": "999", "email": "new@test.com"}

        response = self.client.post(
            self.google_register_url,
            {
                "id_token": "fake",
                "username": "takenusername",
                "city": "Barcelona",
                "language": "es",
                "stationCode": "BCN",
                "gardenName": "Garden",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Username already taken", response.data["error"])

    @patch("api.views.views_profile_operations.verify_google_token")
    def test_google_register_success(self, mock_verify):
        """Registro exitoso con Google"""
        mock_verify.return_value = {
            "sub": "123456",
            "email": "newgoogle@test.com",
            "name": "Google User",
        }

        response = self.client.post(
            self.google_register_url,
            {
                "id_token": "fake",
                "username": "googleuser",
                "city": "Barcelona",
                "language": "es",
                "stationCode": "BCN",
                "gardenName": "Mi Jardín",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("token", response.data)
        self.assertEqual(response.data["username"], "googleuser")

        # Verificar que se creó todo
        user = User.objects.get(username="googleuser")
        self.assertEqual(user.google_id, "123456")
        self.assertTrue(Inventory.objects.filter(user=user).exists())
        self.assertTrue(Garden.objects.filter(user=user, name="Mi Jardín").exists())
        self.assertEqual(Pot.objects.filter(garden__user=user).count(), 16)

    @patch("api.views.views_profile_operations.verify_google_token")
    def test_google_register_creates_complete_setup(self, mock_verify):
        """Registro crea usuario, inventario, jardín y macetas"""
        mock_verify.return_value = {"sub": "new_id", "email": "complete@test.com"}

        response = self.client.post(
            self.google_register_url,
            {
                "id_token": "fake",
                "username": "completeuser",
                "city": "Madrid",
                "language": "en",
                "stationCode": "MAD",
                "gardenName": "Complete Garden",
            },
            format="json",
        )

        user = User.objects.get(username="completeuser")
        self.assertEqual(user.city, "Madrid")
        self.assertEqual(user.language, "en")
        self.assertEqual(user.stationCode, "MAD")

        garden = Garden.objects.get(user=user)
        self.assertEqual(garden.name, "Complete Garden")

        pots = Pot.objects.filter(garden=garden)
        self.assertEqual(pots.count(), 16)
