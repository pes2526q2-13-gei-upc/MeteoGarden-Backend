from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from api.models import Event, EventsCategory


@pytest.fixture
def some_categories(db):
    c1 = EventsCategory.objects.create(id=1, name="Música")
    c2 = EventsCategory.objects.create(id=2, name="Turisme")
    return [c1, c2]


@pytest.fixture
def test_events(some_categories):
    base = datetime.now()
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


#
# FUNCIONS DE DOMINI (unitats)
#


@patch("api.views.views_event.translate_text", side_effect=lambda xs, lang: xs)
@pytest.mark.django_db
def test_get_all_events_returns_expected(test_events, mock_trad):
    from api.views.views_event import get_all_events

    date = datetime.now().isoformat()
    data = get_all_events(date, lang="cat")
    assert isinstance(data, list)
    assert len(data) == 2
    for ev in data:
        assert "title" in ev and "city" in ev and "category" in ev


@patch("api.views.views_event.translate_text", side_effect=lambda xs, lang: xs)
@pytest.mark.django_db
def test_get_all_events_by_city_ok(test_events, mock_trad):
    from api.views.views_event import get_all_events

    date = datetime.now().isoformat()
    data = get_all_events(date, lang="cat", city="tarragona", cat=None)
    assert len(data) == 1
    assert data[0]["city"].lower() == "tarragona"


@patch("api.views.views_event.translate_text", side_effect=lambda xs, lang: xs)
@pytest.mark.django_db
def test_get_all_events_by_category_ok(test_events, mock_trad, some_categories):
    from api.views.views_event import get_all_events

    date = datetime.now().isoformat()
    data = get_all_events(date, lang="cat", city=None, cat="Música")
    assert len(data) == 1
    assert data[0]["category"]["name"] == "Música"


@pytest.mark.django_db
def test_get_number_of_events_all_and_by_city(test_events):
    from api.views.views_event import get_number_of_events

    now = datetime.now()
    month, year = str(now.month), str(now.year)
    all_events = list(get_number_of_events(month, year, city=None))
    assert all("day" in ev and "total" in ev for ev in all_events)
    total = sum(ev["total"] for ev in all_events)
    assert total >= 2

    events_in_tarragona = list(get_number_of_events(month, year, city="Tarragona"))
    # Com a mínim 1 event a Tarragona
    assert sum(ev["total"] for ev in events_in_tarragona) >= 1


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
    # Títol traduït mockejat
    assert result.title.endswith("[trad]")
    assert hasattr(result, "category")
    assert result.category.name.endswith("[trad]") if result.category else True


@pytest.mark.django_db
def test_get_details_cat_no_translation(test_events):
    from api.views.views_event import get_details

    ev = test_events[0]
    result = get_details(ev.id, lang="cat")
    assert result.title == ev.title


#
# ENDPOINTS HTTP
#


@pytest.mark.django_db
def test_get_events_endpoint(test_events):
    client = APIClient()
    date = datetime.now().date().isoformat()
    url = reverse("getEvents") + f"?date={date}&lang=cat"
    resp = client.get(url)
    assert resp.status_code == 200
    data = resp.json()
    assert "events" in data
    assert type(data["events"]) is list and len(data["events"]) == 2


@pytest.mark.django_db
def test_get_events_by_city_endpoint(test_events):
    client = APIClient()
    date = datetime.now().date().isoformat()
    url = reverse("getEventsByCity") + f"?date={date}&lang=cat&city=Tarragona"
    resp = client.get(url)
    assert resp.status_code == 200
    data = resp.json()
    cities = [ev["city"].lower() for ev in data["events"]]
    assert "tarragona" in cities


@pytest.mark.django_db
def test_get_events_by_category_endpoint(test_events):
    client = APIClient()
    date = datetime.now().date().isoformat()
    url = reverse("getEventsByCategory") + f"?date={date}&lang=cat&category=Música"
    resp = client.get(url)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["events"]) == 1
    assert data["events"][0]["category"]["name"] == "Música"


@pytest.mark.django_db
def test_get_num_events_endpoint(test_events):
    client = APIClient()
    now = datetime.now()
    url = reverse("getNumEvents") + f"?year={now.year}&month={now.month}"
    resp = client.get(url)
    assert resp.status_code == 200
    data = resp.json()
    assert "events" in data
    assert all("day" in e and "total" in e for e in data["events"])


@pytest.mark.django_db
def test_get_num_events_endpoint_with_city(test_events):
    client = APIClient()
    now = datetime.now()
    url = reverse("getNumEvents") + f"?year={now.year}&month={now.month}&city=Tarragona"
    resp = client.get(url)
    assert resp.status_code == 200
    data = resp.json()
    assert all(ev["total"] >= 0 for ev in data["events"])


@pytest.mark.django_db
def test_get_event_detail_endpoint(test_events):
    client = APIClient()
    obj = test_events[0]
    url = reverse("getEventDetail") + f"?id={obj.id}&lang=cat"
    resp = client.get(url)
    assert resp.status_code == 200
    data = resp.json()
    # Ha de contenir camps de l'event serialitzat
    assert "events" in data
    assert data["events"]["id"] == obj.id


@pytest.mark.django_db
def test_get_categories_endpoint(some_categories):
    client = APIClient()
    url = reverse("getCategories")
    resp = client.get(url)
    assert resp.status_code == 200
    cats = resp.json()
    assert isinstance(cats, list)
    assert {"id": some_categories[0].id, "name": some_categories[0].name} in cats


#
# ERROR & EDGE CASES
#


@pytest.mark.django_db
def test_get_all_events_invalid_date():
    from api.views.views_event import get_all_events

    assert get_all_events()("INVALIDDATE", "cat") == []


@pytest.mark.django_db
def test_get_all_events_by_city_empty_city():
    from api.views.views_event import get_all_events

    date = datetime.now().isoformat()
    assert get_all_events(date, lang="cat", city=None, cat=None) == []


@pytest.mark.django_db
def test_get_all_events_by_category_invalid_cat(test_events):
    from api.views.views_event import get_all_events

    date = datetime.now().isoformat()
    assert get_all_events(date, "cat", None, "NOEXIST") == []


@pytest.mark.django_db
def test_get_event_detail_endpoint_not_found():
    client = APIClient()
    url = reverse("getEventDetail") + "?id=UNKNOWN&lang=cat"
    resp = client.get(url)
    assert resp.status_code in (400, 500)  # pot ser un 400 o 500 segons el handler


@pytest.mark.django_db
def test_get_num_events_endpoint_invalid_params():
    client = APIClient()
    url = reverse("getNumEvents")  # sense year ni month
    resp = client.get(url)
    assert resp.status_code == 200
    assert resp.json()["events"] == []
