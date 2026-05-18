from unittest.mock import patch

from django.urls import reverse
from rest_framework.test import APITestCase, APIClient

from api.models import (
    FriendRequest,
    Garden,
    User,
)


class TestFriendsAPI(APITestCase):

    def setUp(self):

        self.client = APIClient()

        self.TEST_PASSWORD = (
            "testpassword123"
        )

        self.u1 = User.objects.create_user(
            username="alice",
            password=self.TEST_PASSWORD,
            email="alice@mail.cat",
            city="Bcn",
            stationCode="0001",
        )

        self.u2 = User.objects.create_user(
            username="bob",
            password=self.TEST_PASSWORD,
            email="bob@mail.cat",
            city="Bcn",
            stationCode="0002",
        )

        Garden.objects.create(
            user=self.u1,
            name="AliceGarden"
        )

        Garden.objects.create(
            user=self.u2,
            name="BobGarden"
        )

    def get_token(self, user):

        self.client.force_authenticate(
            user=user
        )

    ################################
    # search
    ################################

    def test_search_users(self):

        url = reverse(
            "search_users"
        )

        response = self.client.get(
            url,
            {"q": "ali"}
        )

        self.assertEqual(
            response.status_code,
            200
        )

        results = response.json()

        self.assertEqual(
            len(results),
            1
        )

        self.assertEqual(
            results[0]["username"],
            "alice"
        )

    ################################
    # friendship
    ################################

    def test_friendship_flow(self):

        FriendRequest.objects.create(
            requester=self.u1,
            requested=self.u2,
            accepted=True
        )

        self.get_token(
            self.u1
        )

        url = reverse(
            "get_users_friends"
        )

        response = self.client.get(
            url
        )

        self.assertEqual(
            response.status_code,
            200
        )

        friends = response.json()[
            "friends"
        ]

        self.assertEqual(
            friends[0]["username"],
            "bob"
        )

        self.assertEqual(
            friends[0]["garden"],
            "BobGarden"
        )

        self.client.force_authenticate(
            None
        )

        self.get_token(
            self.u1
        )

        url = reverse(
            "delete_friend",
            args=["bob"]
        )

        response = self.client.delete(
            url
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertIn(
            "success",
            response.json()[
                "success"
            ]
        )

        url = reverse(
            "get_users_friends"
        )

        response = self.client.get(
            url
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertEqual(
            response.json()[
                "friends"
            ],
            []
        )

    ################################
    # likes
    ################################

    @patch(
        "api.views.views_friends.notify"
    )
    def test_like_friend_and_state(
        self,
        mock_notify
    ):

        mock_notify.return_value = None

        FriendRequest.objects.create(
            requester=self.u1,
            requested=self.u2,
            accepted=True
        )

        garden = Garden.objects.get(
            user=self.u2
        )

        garden.likes = 0

        garden.save()

        self.get_token(
            self.u1
        )

        url_like = reverse(
            "like_friend",
            args=["bob"]
        )

        response = self.client.get(
            url_like
        )

        self.assertEqual(
            response.status_code,
            200
        )

        data = response.json()

        self.assertFalse(
            data["state"]
        )

        self.assertEqual(
            data["likes"],
            0
        )

        response = self.client.post(
            url_like
        )

        self.assertEqual(
            response.status_code,
            200
        )

        garden.refresh_from_db()

        data = response.json()

        self.assertTrue(
            data["state"]
        )

        self.assertEqual(
            garden.likes,
            1
        )

        response = self.client.get(
            url_like
        )

        data = response.json()

        self.assertTrue(
            data["state"]
        )

        response = self.client.post(
            url_like
        )

        garden.refresh_from_db()

        data = response.json()

        self.assertFalse(
            data["state"]
        )

        self.assertEqual(
            garden.likes,
            0
        )

        self.client.force_authenticate(
            None
        )

        fake = User.objects.create_user(
            username="nofriend",
            password=self.TEST_PASSWORD,
            email="a@b.c",
            city="c",
            stationCode="c",
        )

        self.get_token(
            fake
        )

        url = reverse(
            "like_friend",
            args=["alice"]
        )

        response = self.client.post(
            url
        )

        self.assertIn(
            response.status_code,
            [403,404]
        )

        response = self.client.get(
            url
        )

        self.assertIn(
            response.status_code,
            [403,404]
        )

