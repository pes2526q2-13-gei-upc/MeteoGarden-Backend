from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from api.models import FriendRequest, User


class FriendRequestTests(APITestCase):

    def setUp(self):
        self.user1 = User.objects.create_user(
            username="pepe", email="pepe@test.com", password="1234"
        )

        self.user2 = User.objects.create_user(
            username="juan", email="juan@test.com", password="1234"
        )

        self.user3 = User.objects.create_user(
            username="maria", email="maria@test.com", password="1234"
        )

        self.client.force_authenticate(user=self.user1)

    ############################
    # SEND FRIEND REQUEST
    ############################

    def test_send_request_user_not_exists(self):

        response = self.client.post(
            reverse("sendFriendRequest"), {"requested": "fantasma"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_send_request_to_self(self):

        response = self.client.post(
            reverse("sendFriendRequest"), {"requested": "pepe"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_send_request_already_exists(self):

        FriendRequest.objects.create(
            requester=self.user1, requested=self.user2, accepted=None
        )

        response = self.client.post(
            reverse("sendFriendRequest"), {"requested": "juan"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_send_request_inverse_exists(self):

        FriendRequest.objects.create(
            requester=self.user2, requested=self.user1, accepted=None
        )

        response = self.client.post(
            reverse("sendFriendRequest"), {"requested": "juan"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_send_request_success(self):

        response = self.client.post(
            reverse("sendFriendRequest"), {"requested": "juan"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertTrue(
            FriendRequest.objects.filter(
                requester=self.user1, requested=self.user2
            ).exists()
        )

    ############################
    # ANSWER REQUEST
    ############################

    def test_answer_without_action(self):

        response = self.client.post(
            reverse("answerRequest"), {"requester": "juan"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_answer_requester_not_exists(self):

        response = self.client.post(
            reverse("answerRequest"),
            {"requester": "fantasma", "action": "accept"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_answer_request_not_exists(self):

        response = self.client.post(
            reverse("answerRequest"),
            {"requester": "juan", "action": "accept"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_answer_already_answered(self):

        FriendRequest.objects.create(
            requester=self.user2, requested=self.user1, accepted=True
        )

        response = self.client.post(
            reverse("answerRequest"),
            {"requester": "juan", "action": "accept"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_accept_request(self):

        FriendRequest.objects.create(
            requester=self.user2, requested=self.user1, accepted=None
        )

        response = self.client.post(
            reverse("answerRequest"),
            {"requester": "juan", "action": "accept"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        req = FriendRequest.objects.get(
            requester=self.user2, requested=self.user1, accepted=True
        )

        self.assertTrue(req.accepted)

    def test_invalid_action(self):

        FriendRequest.objects.create(
            requester=self.user2, requested=self.user1, accepted=None
        )

        response = self.client.post(
            reverse("answerRequest"),
            {"requester": "juan", "action": "inventada"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    ############################
    # CANCEL REQUEST
    ############################

    def test_cancelRequest_not_exists(self):

        response = self.client.post(
            reverse("cancelRequest"), {"requested": "juan"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cancelRequest_answered(self):

        FriendRequest.objects.create(
            requester=self.user1, requested=self.user2, accepted=True
        )

        response = self.client.post(
            reverse("cancelRequest"), {"requested": "juan"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cancelRequest_success(self):

        FriendRequest.objects.create(
            requester=self.user1, requested=self.user2, accepted=None
        )

        response = self.client.post(
            reverse("cancelRequest"), {"requested": "juan"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertFalse(
            FriendRequest.objects.filter(
                requester=self.user1, requested=self.user2
            ).exists()
        )
