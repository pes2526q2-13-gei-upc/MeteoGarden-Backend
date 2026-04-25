import json
from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, MagicMock
from datetime import datetime
from api.models import GrowthState, ActiveProduct

MOCK_PATH = 'api.views.views_products'


class TestViewsProductsComprehensive(TestCase):
    def setUp(self):
        self.client = Client()
        try:
            self.url = reverse('use_product')
        except:
            self.url = "/api/use_product/"

    def test_error_invalid_json(self):
        response = self.client.post(self.url, data="invalid-json", content_type="application/json")
        self.assertEqual(response.status_code, 400)

    def test_error_missing_data(self):
        payload = {"username": "user1"}
        response = self.client.post(self.url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 400)

    @patch(f'{MOCK_PATH}.get_object_or_404')
    def test_error_user_not_found(self, mock_get):
        from django.http import Http404
        mock_get.side_effect = Http404("User not found")
        payload = {"username": "no", "garden_name": "g", "pot_number": 1, "product_name": "p"}
        response = self.client.post(self.url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 400)

    @patch(f'{MOCK_PATH}.get_object_or_404')
    @patch(f'{MOCK_PATH}.apply_product')
    def test_success_instant_product(self, mock_apply, mock_get):
        mock_user, mock_pot, mock_plant, mock_product = MagicMock(), MagicMock(), MagicMock(), MagicMock()
        mock_plant.healthLevel, mock_plant.waterLevel, mock_plant.growthPhase = 100, 100, "growth"
        mock_product.name, mock_product.isInstant = "Poció", True

        mock_get.side_effect = [mock_user, mock_pot, mock_plant, mock_product]

        payload = {"username": "u", "garden_name": "g", "pot_number": 1, "product_name": "Poció"}
        response = self.client.post(self.url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 200)

    @patch(f'{MOCK_PATH}.get_object_or_404')
    @patch(f'{MOCK_PATH}.apply_product')
    @patch(f'{MOCK_PATH}.ActiveProduct.objects.filter')
    def test_success_duration_product(self, mock_active_filter, mock_apply, mock_get):
        mock_user, mock_pot, mock_plant, mock_product = MagicMock(), MagicMock(), MagicMock(), MagicMock()
        mock_plant.healthLevel, mock_plant.waterLevel, mock_plant.growthPhase = 100, 100, "growth"
        mock_product.name, mock_product.isInstant, mock_product.durationHours = "Escut", False, 10

        mock_get.side_effect = [mock_user, mock_pot, mock_plant, mock_product]

        mock_active = MagicMock()
        mock_active.applied_at = datetime(2024, 5, 20, 10, 0, 0)
        mock_active_filter.return_value.latest.return_value = mock_active

        payload = {"username": "u", "garden_name": "g", "pot_number": 1, "product_name": "Escut"}
        response = self.client.post(self.url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("2024-05-20T20:00:00", response.json()["expiresAt"])

    @patch(f'{MOCK_PATH}.get_object_or_404')
    @patch(f'{MOCK_PATH}.apply_product')
    @patch(f'{MOCK_PATH}.ActiveProduct.objects.filter')
    def test_error_active_product_does_not_exist(self, mock_active_filter, mock_apply, mock_get):
        mock_product = MagicMock(isInstant=False)
        mock_get.side_effect = [MagicMock(), MagicMock(), MagicMock(), mock_product]
        mock_active_filter.return_value.latest.side_effect = ActiveProduct.DoesNotExist

        payload = {"username": "u", "garden_name": "g", "pot_number": 1, "product_name": "p"}
        response = self.client.post(self.url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 404)

    @patch(f'{MOCK_PATH}.get_object_or_404')
    @patch(f'{MOCK_PATH}.apply_product')
    def test_generic_exception(self, mock_apply, mock_get):
        mock_get.side_effect = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]
        mock_apply.side_effect = Exception("Boom")

        payload = {"username": "u", "garden_name": "g", "pot_number": 1, "product_name": "p"}
        response = self.client.post(self.url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 400)