from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from ..models import AlbumEntry, Image, Plant, User


class GetUserAlbumTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/api/album/"
        self.user = User.objects.create(username="anna")
        self.client.force_authenticate(user=self.user)
        self.plant1 = Plant.objects.create(
            scientificName="Solanum lycopersicum", minTemperature=-10, maxTemperature=40
        )
        self.plant2 = Plant.objects.create(
            scientificName="Ocimum basilicum", minTemperature=-50, maxTemperature=50
        )

        AlbumEntry.objects.create(user=self.user, plant=self.plant1)
        AlbumEntry.objects.create(user=self.user, plant=self.plant2)

        img_bytes = b"\x89PNG\r\n\x1a\nfakepng"
        file1 = SimpleUploadedFile("p1.png", img_bytes, content_type="image/png")
        file2 = SimpleUploadedFile("p2.png", img_bytes, content_type="image/png")

        self.image1 = Image.objects.create(plant=self.plant1, url=file1)
        self.image2 = Image.objects.create(plant=self.plant2, url=file2)

    def test_get_user_album_returns_image_urls_for_user(self):

        response = self.client.get(self.url, {"username": "anna"})

        self.assertEqual(response.status_code, 200)

        self.assertIsInstance(response.data, list)

        expected = {self.image1.url.url, self.image2.url.url}
        self.assertEqual(set(response.data), expected)

    def test_get_user_album_user_not_found_returns_404(self):
        response = self.client.get(self.url, {"username": "no-existeix"})
        self.assertEqual(response.status_code, 404)
