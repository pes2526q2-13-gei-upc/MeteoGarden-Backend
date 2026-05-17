import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from api.models import FriendRequest, Garden, User


@pytest.mark.django_db
class TestFriendsAPI:
    def setup_method(self):
        self.client = APIClient()
        self.TEST_PASSWORD = "testpassword123"

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
        Garden.objects.create(user=self.u1, name="AliceGarden")
        Garden.objects.create(user=self.u2, name="BobGarden")

    def get_token(self, user):
        self.client.force_authenticate(user)

    def test_search_users(self):
        url = reverse("search_users")
        r = self.client.get(url, {"q": "ali"})
        assert r.status_code == 200
        results = r.json()
        assert len(results) == 1
        assert results[0]["username"] == "alice"

    def test_friendship_flow(self):
        FriendRequest.objects.create(
            requester=self.u1, requested=self.u2, accepted=True
        )

        self.get_token(self.u1)
        url = reverse("get_users_friends")
        r = self.client.get(url)
        assert r.status_code == 200
        friends = r.json()["friends"]
        assert friends[0]["username"] == "bob"
        assert friends[0]["garden"] == "BobGarden"
        self.client.force_authenticate(None)

        # Delete friend
        self.get_token(self.u1)
        url = reverse("delete_friend", args=["bob"])
        r = self.client.delete(url)
        assert r.status_code == 200
        assert "success" in r.json()["success"]

        # Now, friendship should be gone
        url = reverse("get_users_friends")
        r = self.client.get(url)
        assert r.status_code == 200
        assert r.json()["friends"] == []

    def test_like_friend_and_state(self, monkeypatch):
        monkeypatch.setattr(
            "api.views.views_friends.notify", lambda *args, **kwargs: None
        )

        FriendRequest.objects.create(
            requester=self.u1, requested=self.u2, accepted=True
        )
        garden = Garden.objects.get(user=self.u2)
        garden.likes = 0
        garden.save()

        self.get_token(self.u1)
        url_like = reverse("like_friend", args=["bob"])

        # Initial like state (should be False)
        r = self.client.get(url_like)
        assert r.status_code == 200
        data = r.json()
        assert data["state"] is False
        assert data["likes"] == 0

        # Like bob's garden
        r = self.client.post(url_like)
        assert r.status_code == 200
        garden.refresh_from_db()
        data = r.json()
        assert data["state"] is True
        assert garden.likes == 1
        assert data["likes"] == 1

        # State like should now be True
        r = self.client.get(url_like)
        assert r.status_code == 200
        data = r.json()
        assert data["state"] is True
        assert data["likes"] == 1

        # Dislike (toggle again)
        r = self.client.post(url_like)
        assert r.status_code == 200
        garden.refresh_from_db()
        data = r.json()
        assert data["state"] is False
        assert garden.likes == 0

        self.client.force_authenticate(None)
        fake = User.objects.create_user(
            username="nofriend",
            password=self.TEST_PASSWORD,
            email="a@b.c",
            city="c",
            stationCode="c",
        )
        self.get_token(fake)
        url = reverse("like_friend", args=["alice"])
        r = self.client.post(url)
        assert r.status_code in [403, 404]

        # This GET should also return 403 or 404
        r = self.client.get(url)
        assert r.status_code in [403, 404]
