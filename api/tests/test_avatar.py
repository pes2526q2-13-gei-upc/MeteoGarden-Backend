from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from api.models import Avatar, User


@override_settings(MEDIA_URL="/media/")
class AvatarViewsTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="password123")

    def test_avatar_images_get_returns_expected_structure(self):
        url = reverse("avatar_images")
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()

        # top-level keys
        self.assertIn("accessories", data)
        self.assertIn("body", data)
        self.assertIn("clothing", data)
        self.assertIn("eye", data)
        self.assertIn("expression", data)
        self.assertIn("hair", data)
        self.assertIn("facialHair", data)

        # sanity checks for URL formatting (independent of MEDIA_URL being S3 or /media/)
        self.assertEqual(data["accessories"][0]["id"], 1)
        self.assertTrue(
            data["accessories"][0]["url"].endswith("/avatar/accessories/1.png"),
            msg=f"Unexpected accessories[0].url={data['accessories'][0]['url']}",
        )

        self.assertEqual(data["body"][0]["id"], 1)
        self.assertTrue(
            data["body"][0]["url"].endswith("/avatar/body/1.png"),
            msg=f"Unexpected body[0].url={data['body'][0]['url']}",
        )

        self.assertIn("happy", data["expression"])
        self.assertIn("sad", data["expression"])
        self.assertIn("blond", data["hair"])
        self.assertIn("dark", data["hair"])

    def test_get_user_avatar_user_not_found_returns_404(self):
        url = reverse("user_avatar", kwargs={"username": "missing"})
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(res.json(), {"user": "User not found."})

    def test_get_user_avatar_returns_avatar_urls(self):
        Avatar.objects.create(
            user=self.user,
            accessories="1",  # Recorda que ara és un CharField!
            body="1",
            clothing="1",
            eye="1",
            expression="happy",
            expression_variant="0",
            hair_color="blond",
            hair_style="1",
            facial_hair="1",
            facial_hair_color="dark",
        )

        self.client.force_login(self.user)

        url = reverse("user_avatar", kwargs={"username": self.user.username})
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()

        # independent of MEDIA_URL value
        self.assertTrue(data["accessories"].endswith("/avatar/accessories/1.png"))
        self.assertTrue(data["body"].endswith("/avatar/body/1.png"))
        self.assertTrue(data["clothing"].endswith("/avatar/clothing/1.png"))
        self.assertTrue(data["eye"].endswith("/avatar/eye/1.png"))
        self.assertTrue(data["expression"].endswith("/avatar/expression/happy/0.png"))
        self.assertTrue(data["hair"].endswith("/avatar/hair/blond/1.png"))
        self.assertTrue(data["facialHair"].endswith("/avatar/facialHair/1/dark.png"))

    def test_save_avatar_requires_authentication_or_returns_404_user(self):
        url = reverse("save_avatar", kwargs={"username": self.user.username})
        res = self.client.post(url, data={"body": 2}, format="json")

        self.assertIn(
            res.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND),
        )

    def test_save_avatar_post_creates_avatar_and_returns_201(self):
        self.client.login(username="alice", password="password123")

        url = reverse("save_avatar", kwargs={"username": self.user.username})
        payload = {
            "accessories": 2,
            "body": 3,
            "clothing": 4,
            "eye": 5,
            "expression": "sad",
            "expression_variant": 2,
            "hair_color": "brown",
            "hair_style": 6,
            "facial_hair": 1,
            "facial_hair_color": "blond",
        }
        res = self.client.post(url, data=payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        avatar = Avatar.objects.get(user=self.user)
        self.assertEqual(avatar.body, '3')
        self.assertEqual(avatar.expression, "sad")
        self.assertEqual(avatar.expression_variant, '2')

        data = res.json()
        self.assertTrue(data["body"].endswith("/avatar/body/3.png"))
        self.assertTrue(data["expression"].endswith("/avatar/expression/sad/2.png"))

    def test_save_avatar_put_updates_existing_avatar_and_returns_200(self):
        self.client.login(username="alice", password="password123")

        Avatar.objects.create(
            user=self.user,
            accessories=1,
            body=1,
            clothing=1,
            eye=1,
            expression="happy",
            expression_variant=0,
            hair_color="blond",
            hair_style=1,
            facial_hair=1,
            facial_hair_color="dark",
        )

        url = reverse("save_avatar", kwargs={"username": self.user.username})
        res = self.client.put(url, data={"body": 4, "hair_color": "dark"}, format="json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        avatar = Avatar.objects.get(user=self.user)
        self.assertEqual(avatar.body, '4')
        self.assertEqual(avatar.hair_color, "dark")