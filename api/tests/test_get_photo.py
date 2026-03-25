from unittest.mock import MagicMock, patch

from django.test import TestCase

from api.models import Garden, Image, Plant, PlantInGarden, Pot, User
from api.serializer import PotSerializer


class PotSerializerImageUrlTest(TestCase):
    """
    Unit tests para PotSerializer.get_plant().
    S3 se mockea: no se hace ninguna llamada real a AWS.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="pass",
            city="Barcelona",
            stationCode="0001",
        )
        self.garden = Garden.objects.create(user=self.user, name="Mi jardín")
        self.plant = Plant.objects.create(
            scientificName="Rosa canina",
            commonName="Rosal silvestre",
            minTemperature=5.0,
            maxTemperature=35.0,
        )
        self.pot = Pot.objects.create(garden=self.garden, number=1, occupied=True)
        self.planting = PlantInGarden.objects.create(
            pot=self.pot,
            plant=self.plant,
            growthPhase="growth",
            healthLevel=80.0,
            waterLevel=60.0,
        )

    # ------------------------------------------------------------------
    # Caso 1: la planta tiene imagen → image_url debe ser la URL de S3
    # ------------------------------------------------------------------
    @patch("api.serializer.Image.objects.filter")
    def test_image_url_present_when_image_exists(self, mock_filter):
        """El serializer devuelve la URL de S3 cuando existe una imagen."""
        fake_image = MagicMock(spec=Image)
        fake_image.url.url = (
            "https://mybucket.s3.amazonaws.com/plants/rosa_canina/photo.jpg"
        )

        mock_filter.return_value.first.return_value = fake_image

        serializer = PotSerializer(self.pot)
        plant_data = serializer.data["plant"]

        self.assertIsNotNone(plant_data)
        self.assertEqual(
            plant_data["image_url"],
            "https://mybucket.s3.amazonaws.com/plants/rosa_canina/photo.jpg",
        )

    # ------------------------------------------------------------------
    # Caso 2: la planta NO tiene imagen → image_url debe ser None
    # ------------------------------------------------------------------
    @patch("api.serializer.Image.objects.filter")
    def test_image_url_none_when_no_image(self, mock_filter):
        """El serializer devuelve None en image_url si no hay imagen."""
        mock_filter.return_value.first.return_value = None

        serializer = PotSerializer(self.pot)
        plant_data = serializer.data["plant"]

        self.assertIsNotNone(plant_data)
        self.assertIsNone(plant_data["image_url"])

    # ------------------------------------------------------------------
    # Caso 3: el pot está vacío → plant debe ser None
    # ------------------------------------------------------------------
    def test_empty_pot_returns_null_plant(self):
        """Un pot sin PlantInGarden devuelve plant=None."""
        empty_pot = Pot.objects.create(garden=self.garden, number=2, occupied=False)

        serializer = PotSerializer(empty_pot)
        self.assertIsNone(serializer.data["plant"])

    # ------------------------------------------------------------------
    # Caso 4: la respuesta del endpoint incluye image_url en el JSON
    # ------------------------------------------------------------------
    @patch("api.serializer.Image.objects.filter")
    def test_garden_plants_endpoint_returns_image_url(self, mock_filter):
        """El endpoint /garden_plants/ incluye image_url en la respuesta JSON."""
        from django.test import Client

        fake_image = MagicMock(spec=Image)
        fake_image.url.url = (
            "https://mybucket.s3.amazonaws.com/plants/rosa_canina/photo.jpg"
        )
        mock_filter.return_value.first.return_value = fake_image

        client = Client()
        response = client.get(
            f"/api/users/{self.user.username}/gardens/{self.garden.name}/plants/"
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Busca el pot que tiene planta
        pot_data = next((p for p in data if p["plant"] is not None), None)
        self.assertIsNotNone(pot_data)
        self.assertIn("image_url", pot_data["plant"])
        self.assertEqual(
            pot_data["plant"]["image_url"],
            "https://mybucket.s3.amazonaws.com/plants/rosa_canina/photo.jpg",
        )

    # ------------------------------------------------------------------
    # Caso 5: la URL generada sigue el patrón esperado de S3
    # ------------------------------------------------------------------
    @patch("api.serializer.Image.objects.filter")
    def test_image_url_matches_s3_pattern(self, mock_filter):
        """La URL devuelta es una URL de S3 con el formato correcto."""
        s3_url = "https://mybucket.s3.amazonaws.com/plants/rosa_canina/photo.jpg"
        fake_image = MagicMock(spec=Image)
        fake_image.url.url = s3_url
        mock_filter.return_value.first.return_value = fake_image

        serializer = PotSerializer(self.pot)
        image_url = serializer.data["plant"]["image_url"]

        self.assertTrue(image_url.startswith("https://"))
        self.assertIn("s3.amazonaws.com", image_url)
        self.assertTrue(image_url.endswith((".jpg", ".jpeg", ".png", ".webp")))
