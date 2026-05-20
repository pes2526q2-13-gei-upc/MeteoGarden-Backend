from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework.test import (
    APIClient,
    APITestCase,
)

from api.models import (
    Plant,
    User,
)


class TestIdentifyPlantAPI(APITestCase):
    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create_user(
            username="alice",
            password="test123",
            email="alice@mail.cat",
            city="Bcn",
            stationCode="0001",
            language="english",
        )

        self.client.force_authenticate(user=self.user)

        self.image = SimpleUploadedFile(
            "leaf.jpg", b"fake-image-content", content_type="image/jpeg"
        )

    ################################
    # validations
    ################################

    def test_username_required(self):

        url = reverse("identifyPlant")

        response = self.client.post(url, {}, format="multipart")

        self.assertEqual(response.status_code, 400)

        self.assertEqual(response.json(), {"error": "Username required"})

    def test_image_required(self):

        url = reverse("identifyPlant")

        response = self.client.post(
            url, {"username": "alice", "organ": "leaf"}, format="multipart"
        )

        self.assertEqual(response.status_code, 400)

        self.assertEqual(response.json(), {"image": "Image file is required."})

    def test_invalid_organ(self):

        url = reverse("identifyPlant")

        response = self.client.post(
            url,
            {"username": "alice", "image": self.image, "organ": "root"},
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)

        self.assertIn("Invalid value", response.json()["organs"])

    ################################
    # plantnet
    ################################

    @patch("api.views.views_identify.translate_text")
    @patch("api.views.views_identify.update_photo_missions")
    @patch("api.views.views_identify.Inventory.addSeed")
    @patch("api.views.views_identify.getInfoPlant")
    @patch("api.views.views_identify.requests.post")
    @patch("api.views.views_identify.os.getenv")
    def test_identify_success(
        self,
        mock_env,
        mock_post,
        mock_info,
        mock_seed,
        mock_missions,
        mock_translate,
    ):

        mock_translate.side_effect = lambda text, lang: text

        mock_env.return_value = "fake_key"

        Plant.objects.create(
            scientificName="Monstera deliciosa",
            commonName="Monstera",
            family="Araceae",
            minTemperature=10,
            maxTemperature=30,
        )

        mock_response = mock_post.return_value

        mock_response.status_code = 200

        mock_response.json.return_value = {
            "results": [
                {
                    "score": 0.95,
                    "species": {
                        "scientificName": "Monstera deliciosa",
                        "commonNames": ["Monstera"],
                        "family": {"scientificNameWithoutAuthor": "Araceae"},
                    },
                }
            ]
        }

        url = reverse("identifyPlant")

        response = self.client.post(
            url,
            {"username": "alice", "image": self.image, "organ": "leaf"},
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)

        data = response.json()

        self.assertEqual(data["plant"]["scientificName"], "Monstera deliciosa")

        self.assertEqual(data["plant"]["commonName"], "Monstera")

        self.assertEqual(data["plant"]["family"], "Araceae")

        self.assertEqual(data["plantnet"]["score"], 0.95)

        mock_info.assert_called_once()

        mock_seed.assert_called_once()

        mock_missions.assert_called_once()

    ################################
    # errors
    ################################

    @patch("api.views.views_identify.os.getenv")
    def test_api_key_missing(self, mock_env):

        mock_env.return_value = None

        url = reverse("identifyPlant")

        response = self.client.post(
            url,
            {"username": "alice", "image": self.image, "organ": "leaf"},
            format="multipart",
        )

        self.assertEqual(response.status_code, 500)

    @patch("api.views.views_identify.translate_text")
    @patch("api.views.views_identify.os.getenv")
    @patch("api.views.views_identify.requests.post")
    def test_plantnet_error(self, mock_post, mock_env, mock_translate):

        mock_translate.side_effect = lambda text, lang: text

        mock_env.return_value = "fake_key"

        mock_post.return_value.status_code = 500

        mock_post.return_value.text = "error"

        url = reverse("identifyPlant")

        response = self.client.post(
            url,
            {"username": "alice", "image": self.image, "organ": "leaf"},
            format="multipart",
        )

        self.assertEqual(response.status_code, 502)

    @patch("api.views.views_identify.translate_text")
    @patch("api.views.views_identify.os.getenv")
    @patch("api.views.views_identify.requests.post")
    def test_no_results(self, mock_post, mock_env, mock_translate):

        mock_translate.side_effect = lambda text, lang: text

        mock_env.return_value = "fake_key"

        mock_post.return_value.status_code = 200

        mock_post.return_value.json.return_value = {"results": []}

        url = reverse("identifyPlant")

        response = self.client.post(
            url,
            {"username": "alice", "image": self.image, "organ": "leaf"},
            format="multipart",
        )

        self.assertEqual(response.status_code, 422)