import os
from unittest.mock import Mock

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def image_file():
    # No cal que sigui un PNG real per la majoria de casos; però si el teu ImageField valida imatges,
    # pots posar bytes d'un PNG mínim.
    return SimpleUploadedFile(
        "test.png",
        b"\x89PNG\r\n\x1a\n" + b"0" * 100,
        content_type="image/png",
    )


@pytest.fixture
def identify_url():
    return reverse("identifyPlant")


@pytest.fixture
def test_user(db):
    from api.models import User

    return User.objects.create(username="testuser")


def _mock_plantnet_response(status_code=200, json_payload=None, text="ERR"):
    resp = Mock()
    resp.status_code = status_code
    resp.text = text
    if json_payload is None:
        json_payload = {}
    resp.json.return_value = json_payload
    return resp


@pytest.mark.django_db
def test_identifyPlant_missing_image_returns_400(
    api_client, identify_url, test_user, monkeypatch
):
    r = api_client.post(
        identify_url, data={"username": test_user.username}, format="multipart"
    )
    assert r.status_code == 400
    assert r.json() == {"image": "Image file is required."}


@pytest.mark.django_db
def test_identifyPlant_invalid_organ_returns_400(
    api_client, identify_url, test_user, image_file, monkeypatch
):
    r = api_client.post(
        identify_url,
        data={"username": test_user.username, "image": image_file, "organs": "root"},
        format="multipart",
    )
    assert r.status_code == 400
    body = r.json()
    assert "organs" in body
    assert "Invalid value" in body["organs"]


@pytest.mark.django_db
def test_identifyPlant_missing_api_key_returns_500(
    api_client, identify_url, test_user, image_file, monkeypatch
):
    monkeypatch.setattr(os, "getenv", lambda k: None)

    r = api_client.post(
        identify_url,
        data={"username": test_user.username, "image": image_file},
        format="multipart",
    )
    assert r.status_code == 500
    assert r.json() == {"detail": "PLANTNET_API_KEY is not configured."}


@pytest.mark.django_db
def test_identifyPlant_plantnet_non_200_returns_502(
    api_client, identify_url, test_user, image_file, monkeypatch
):
    monkeypatch.setattr(os, "getenv", lambda k: "KEY")
    monkeypatch.setattr(
        "api.views.views_identify.requests.post",
        lambda *a, **kw: _mock_plantnet_response(status_code=503, text="service down"),
    )

    r = api_client.post(
        identify_url,
        data={"username": test_user.username, "image": image_file},
        format="multipart",
    )
    assert r.status_code == 502
    body = r.json()
    assert body["detail"] == "PlantNet identification failed."
    assert body["status_code"] == 503
    assert "service down" in body["body"]


@pytest.mark.django_db
def test_identifyPlant_no_results_returns_422(
    api_client, identify_url, test_user, image_file, monkeypatch
):
    monkeypatch.setattr(os, "getenv", lambda k: "KEY")
    monkeypatch.setattr(
        "api.views.views_identify.requests.post",
        lambda *a, **kw: _mock_plantnet_response(
            status_code=200,
            json_payload={"results": []},
        ),
    )

    r = api_client.post(
        identify_url,
        data={"username": test_user.username, "image": image_file},
        format="multipart",
    )
    assert r.status_code == 422
    assert r.json() == {"detail": "No identification results."}


@pytest.mark.django_db
def test_identifyPlant_missing_scientific_name_returns_422(
    api_client, identify_url, test_user, image_file, monkeypatch
):
    monkeypatch.setattr(os, "getenv", lambda k: "KEY")
    monkeypatch.setattr(
        "api.views.views_identify.requests.post",
        lambda *a, **kw: _mock_plantnet_response(
            status_code=200,
            json_payload={"results": [{"species": {}}]},
        ),
    )

    r = api_client.post(
        identify_url,
        data={"username": test_user.username, "image": image_file},
        format="multipart",
    )
    assert r.status_code == 422
    assert r.json() == {"detail": "PlantNet response missing scientific name."}


@pytest.mark.django_db
def test_identifyPlant_success_201_creates_image_and_returns_payload(
    api_client, identify_url, test_user, image_file, monkeypatch
):
    from api.models import Image, Plant, User

    monkeypatch.setattr(os, "getenv", lambda k: "KEY")
    monkeypatch.setattr(
        "api.views.views_identify.requests.post",
        lambda *a, **kw: _mock_plantnet_response(
            status_code=200,
            json_payload={
                "results": [
                    {
                        "score": 0.91,
                        "species": {"scientificNameWithoutAuthor": "Rosa canina"},
                    }
                ]
            },
        ),
    )

    def fake_getInfoPlant(scientific_name, *args, **kwargs):
        plant, _ = Plant.objects.get_or_create(
            scientificName=scientific_name,
            defaults={
                "commonName": "Rose",
                "family": "Rosaceae",
                "minTemperature": 60,
                "maxTemperature": 90,
            },
        )
        return plant

    monkeypatch.setattr("api.views.views_identify.getInfoPlant", fake_getInfoPlant)

    r = api_client.post(
        identify_url,
        data={"username": test_user.username, "image": image_file, "organs": "leaf"},
        format="multipart",
    )
    assert r.status_code == 201
    body = r.json()

    assert body["plant"]["scientificName"] == "Rosa canina"
    assert body["plant"]["commonName"] == "Rose"
    assert body["plant"]["family"] == "Rosaceae"
    assert body["plantnet"]["score"] == 0.91

    assert Image.objects.count() == 1
    img = Image.objects.first()
    assert img.url.name
