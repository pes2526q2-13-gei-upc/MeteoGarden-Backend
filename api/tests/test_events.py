from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from django.urls import reverse
from django.utils import timezone  # Per evitar RuntimeWarnings de naive datetimes
from rest_framework.test import APIClient

from api.models import Event, EventsCategory

# --- FIXTURES ---


@pytest.fixture
def some_categories(db):
    c1 = EventsCategory.objects.create(id=1, name="Música")
    c2 = EventsCategory.objects.create(id=2, name="Turisme")
    return [c1, c2]


@pytest.fixture
def test_events(some_categories):
    # Utilitzem timezone.now() per evitar avisos de naive datetime
    base = timezone.now()
    e1 = Event.objects.create(
        id="1",
        title="Concert Rock",
        subtitle="Gran concert",
        description="Desc 1",
        start_date=base - timedelta(days=2),
        end_date=base + timedelta(days=2),
        category=some_categories[0],
        price=10,
        tags=["concert"],
        city="Tarragona",
        street="Rambla Vella",
    )
    e2 = Event.objects.create(
        id="2",
        title="Ruta modernista",
        subtitle="Descobreix la ciutat",
        description="Desc 2",
        start_date=base - timedelta(days=1),
        end_date=base + timedelta(days=2),
        category=some_categories[1],
        price=0,
        tags=["ruta"],
        city="Reus",
        street="Plaça Mercadal",
    )
    return [e1, e2]


# --- FUNCIONS DE DOMINI ---


# CRITICAL: El mock (mock_trad) ha d'anar DESPRÉS de la fixture (test_events)
@patch("api.views.views_event.translate_text", side_effect=lambda xs, lang: xs)
@pytest.mark.django_db
def test_get_all_events_returns_expected(test_events, mock_trad):
    from api.views.views_event import get_all_events

    date = timezone.now().isoformat()
    # Ordre correcte de paràmetres: date, lang, city, cat
    data = get_all_events(date, "cat", None, None)
    assert isinstance(data, list)
    assert len(data) == 2


@patch("api.views.views_event.translate_text", side_effect=lambda xs, lang: xs)
@pytest.mark.django_db
def test_get_all_events_by_city_ok(test_events, mock_trad):
    from api.views.views_event import get_all_events

    date = timezone.now().isoformat()
    data = get_all_events(date, "cat", "tarragona", None)
    assert len(data) == 1
    assert data[0]["city"].lower() == "tarragona"


@patch("api.views.views_event.translate_text", side_effect=lambda xs, lang: xs)
@pytest.mark.django_db
def test_get_all_events_by_category_ok(test_events, mock_trad, some_categories):
    from api.views.views_event import get_all_events

    date = timezone.now().isoformat()
    data = get_all_events(date, "cat", None, "Música")
    assert len(data) == 1
    assert data[0]["category"]["name"] == "Música"


@pytest.mark.django_db
def test_get_number_of_events_all_and_by_city(test_events):
    from api.views.views_event import get_number_of_events

    now = timezone.now()
    month, year = str(now.month), str(now.year)
    all_events = list(get_number_of_events(month, year, city=None))
    total = sum(ev["total"] for ev in all_events)
    assert total >= 2


@patch(
    "api.views.views_event.translate_text",
    side_effect=lambda xs, lang: [
        a + " [trad]" if isinstance(a, str) else a for a in xs
    ],
)
@pytest.mark.django_db
def test_get_details_translates_fields(test_events, mock_trad):
    from api.views.views_event import get_details

    ev = test_events[0]
    result = get_details(ev.id, lang="es")
    assert "[trad]" in result.title
    assert "[trad]" in result.category.name


# --- ENDPOINTS HTTP ---


@pytest.mark.django_db
def test_get_events_endpoint(test_events):
    client = APIClient()
    date = timezone.now().date().isoformat()
    url = reverse("events") + f"?date={date}&lang=cat"
    resp = client.get(url)
    assert resp.status_code == 200
    assert len(resp.data["events"]) == 2


@pytest.mark.django_db
def test_get_event_detail_endpoint_not_found(db):
    client = APIClient()
    url = reverse("event_detail") + "?id=999999&lang=cat"
    resp = client.get(url)
    # Amb el try/except que hem posat a la vista, ara retornarà 404
    assert resp.status_code == 404
