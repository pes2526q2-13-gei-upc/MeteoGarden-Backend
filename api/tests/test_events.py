from datetime import datetime, timedelta
from unittest.mock import patch

from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from api.models import Event, EventsCategory


class EventTests(APITestCase):

    def setUp(self):

        self.c1 = EventsCategory.objects.create(id=1, name="Música")

        self.c2 = EventsCategory.objects.create(id=2, name="Turisme")

        base = timezone.now()

        self.e1 = Event.objects.create(
            id="1",
            title="Concert Rock",
            subtitle="Gran concert",
            description="Desc 1",
            start_date=base - timedelta(days=2),
            end_date=base + timedelta(days=2),
            category=self.c1,
            price=10,
            tags=["concert"],
            city="Tarragona",
            street="Rambla Vella",
        )

        self.e2 = Event.objects.create(
            id="2",
            title="Ruta modernista",
            subtitle="Descobreix la ciutat",
            description="Desc 2",
            start_date=base - timedelta(days=1),
            end_date=base + timedelta(days=2),
            category=self.c2,
            price=0,
            tags=["ruta"],
            city="Reus",
            street="Plaça Mercadal",
        )

        self.events = [self.e1, self.e2]

    # --- FUNCIONS DE DOMINI ---

    def test_get_all_events_returns_expected(self):

        from api.views.views_event import get_all_events

        with patch(
            "api.views.views_event.translate_text", side_effect=lambda xs, lang: xs
        ):

            date = datetime.now().isoformat()

            data = get_all_events(date, lang="cat", city=None, cat=None)

            self.assertIsInstance(data, list)

            self.assertEqual(len(data), 2)

    def test_get_all_events_by_city_ok(self):

        from api.views.views_event import get_all_events

        with patch(
            "api.views.views_event.translate_text", side_effect=lambda xs, lang: xs
        ):

            date = timezone.now().isoformat()

            data = get_all_events(date, "cat", "tarragona", None)

            self.assertEqual(len(data), 1)

            self.assertEqual(data[0]["city"].lower(), "tarragona")

    def test_get_all_events_by_category_ok(self):

        from api.views.views_event import get_all_events

        with patch(
            "api.views.views_event.translate_text", side_effect=lambda xs, lang: xs
        ):

            date = timezone.now().isoformat()

            data = get_all_events(date, "cat", None, "Música")

            self.assertEqual(len(data), 1)

            self.assertEqual(data[0]["category"]["name"], "Música")

    def test_get_number_of_events_all_and_by_city(self):

        from api.views.views_event import get_number_of_events

        now = timezone.now()

        month = str(now.month)

        year = str(now.year)

        all_events = list(get_number_of_events(month, year, city=None, cat=None))

        total = sum(ev["total"] for ev in all_events)

        self.assertGreaterEqual(total, 2)

    def test_get_details_translates_fields(self):

        from api.views.views_event import get_details

        with patch("api.views.views_event.translate_text") as mock_trad:

            mock_trad.side_effect = lambda xs, lang: [
                a + " [trad]" if isinstance(a, str) else a for a in xs
            ]

            result = get_details(self.e1.id, lang="es")

            self.assertIn("[trad]", result.title)

            if result.category:

                self.assertIn("[trad]", result.category.name)

            self.assertTrue(mock_trad.called)

    # --- ENDPOINTS HTTP ---

    def test_get_events_endpoint(self):

        client = APIClient()

        date = timezone.now().date().isoformat()

        url = reverse("events") + f"?date={date}&lang=cat"

        response = client.get(url)

        self.assertEqual(response.status_code, 200)

        self.assertEqual(len(response.data["events"]), 2)

    def test_get_event_detail_endpoint_not_found(self):

        client = APIClient()

        url = reverse("event_detail") + "?id=999999&lang=cat"

        response = client.get(url)

        self.assertEqual(response.status_code, 404)
