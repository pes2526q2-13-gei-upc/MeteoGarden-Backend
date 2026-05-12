from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from rest_framework.test import APIRequestFactory

MODULE_PATH = "api.views.views_info"


@pytest.mark.django_db
class TestHelpers:
    def test_getTemperature_none(self):
        mod = __import__(MODULE_PATH, fromlist=["getTemperature"])
        getTemperature = mod.getTemperature

        assert getTemperature(None, 3) == (None, None)
        assert getTemperature(1, None) == (None, None)

    def test_getTemperature_valid_range(self):
        mod = __import__(MODULE_PATH, fromlist=["getTemperature"])
        getTemperature = mod.getTemperature

        # zone 1 -> min -51.1 ; zone 3 -> max 24 (segons TEMPS_RANGES)
        assert getTemperature(1, 3) == (-51.1, 24.0)

    def test_inferCanFlowerFromGBIF_flowering_class(self, monkeypatch):
        mod = __import__(MODULE_PATH, fromlist=["inferCanFlowerFromGBIF"])
        infer = mod.inferCanFlowerFromGBIF

        def fake_get(*args, **kwargs):
            return SimpleNamespace(
                json=lambda: {"class": "Magnoliopsida", "phylum": "Tracheophyta"}
            )

        monkeypatch.setattr(mod.requests, "get", fake_get)
        assert infer("Rosa canina") is True

    def test_inferCanFlowerFromGBIF_non_flowering_phylum(self, monkeypatch):
        mod = __import__(MODULE_PATH, fromlist=["inferCanFlowerFromGBIF"])
        infer = mod.inferCanFlowerFromGBIF

        def fake_get(*args, **kwargs):
            return SimpleNamespace(
                json=lambda: {"class": "Unknown", "phylum": "Pinophyta"}
            )

        monkeypatch.setattr(mod.requests, "get", fake_get)
        assert infer("Pinus sylvestris") is False

    def test_infer_can_flower_from_gbif_exception_returns_false(self, monkeypatch):
        mod = __import__(MODULE_PATH, fromlist=["inferCanFlowerFromGBIF"])
        infer = mod.inferCanFlowerFromGBIF

        def boom(*args, **kwargs):
            raise RuntimeError("network down")

        monkeypatch.setattr(mod.requests, "get", boom)
        assert infer("Anything") is False

    def test_getInfoFromWikipedia_non_200(self, monkeypatch):
        mod = __import__(MODULE_PATH, fromlist=["getInfoFromWikipedia"])
        getInfo = mod.getInfoFromWikipedia

        def fake_get(*args, **kwargs):
            return SimpleNamespace(status_code=404, json=lambda: {})

        monkeypatch.setattr(mod.requests, "get", fake_get)
        assert getInfo("Rosa canina") == {"canFlower": None, "description": None}

    def test_getInfoFromWikipedia_detects_flowering(self, monkeypatch):
        mod = __import__(MODULE_PATH, fromlist=["getInfoFromWikipedia"])
        getInfo = mod.getInfoFromWikipedia

        def fake_get(*args, **kwargs):
            return SimpleNamespace(
                status_code=200,
                json=lambda: {"extract": "Rosa is a flowering plant.\nMore text..."},
            )

        monkeypatch.setattr(mod.requests, "get", fake_get)
        assert getInfo("Rosa canina")["canFlower"] is True
        assert getInfo("Rosa canina")["description"] == "Rosa is a flowering plant."

    def test_getInfoFromWikipedia_detects_non_flowering_keywords(self, monkeypatch):
        mod = __import__(MODULE_PATH, fromlist=["getInfoFromWikipedia"])
        getInfo = mod.getInfoFromWikipedia

        def fake_get(*args, **kwargs):
            return SimpleNamespace(
                status_code=200,
                json=lambda: {"extract": "Pinus is a conifer (a gymnosperm)."},
            )

        monkeypatch.setattr(mod.requests, "get", fake_get)
        assert getInfo("Pinus sylvestris")["canFlower"] is False


@pytest.mark.django_db
class TestFilterAndPersistence:
    def test_filterInfo_details_none_uses_wikipedia_defaults_and_saves(
        self, monkeypatch
    ):
        mod = __import__(MODULE_PATH, fromlist=["filterInfo"])
        filterInfo = mod.filterInfo

        # evita crida real a wikipedia
        monkeypatch.setattr(
            mod,
            "getInfoFromWikipedia",
            lambda name: {"canFlower": True, "description": "Desc"},
        )
        # espies/mocks sobre persistència i imatges
        save_mock = MagicMock()
        monkeypatch.setattr(mod, "saveOrUpdatePlant", save_mock)

        info = filterInfo("Rosa canina", None, "en")

        assert info["scientificName"] == "Rosa canina"
        assert info["commonName"] is None
        assert info["family"] is None
        assert info["canFlower"] is True
        assert info["minTemperature"] == mod.DEFAULT_MIN_TEMPERATURE
        assert info["maxTemperature"] == mod.DEFAULT_MAX_TEMPERATURE
        assert info["description"] == "Desc"
        save_mock.assert_called_once()

    def test_filterInfo_details_translates_when_lang_not_en_and_details_present(
        self, monkeypatch
    ):
        mod = __import__(MODULE_PATH, fromlist=["filterInfo"])
        filterInfo = mod.filterInfo

        details = {
            "hardiness": {"min": 1, "max": 3},
            "common_name": "rose",
            "family": "Rosaceae",
            "flowers": True,
            "description": "A plant",
        }

        monkeypatch.setattr(mod, "saveOrUpdatePlant", MagicMock())
        monkeypatch.setattr(mod, "translate_text", lambda text, lang: f"[{lang}]{text}")

        info = filterInfo("Rosa canina", details, "ca")

        assert info["commonName"] == "[ca]Rose"  # capitalitzat abans de traduir
        assert info["description"] == "[ca]A plant"
        assert info["minTemperature"] == -51.1
        assert info["maxTemperature"] == 24.0


@pytest.mark.django_db
class TestImportPlantEndpoint:
    def test_importPlant_get_missing_scientificName_returns_400(self):
        mod = __import__(MODULE_PATH, fromlist=["importPlant"])
        view = mod.importPlant

        factory = APIRequestFactory()
        req = factory.get("/importPlant", data={"lang": "en"})
        resp = view(req)

        assert resp.status_code == 400
        assert resp.data["error"] == "scientificName is required"

    def test_importPlant_returns_404_when_getInfoPlant_returns_none(self, monkeypatch):
        mod = __import__(MODULE_PATH, fromlist=["importPlant"])
        view = mod.importPlant

        monkeypatch.setattr(mod, "getInfoPlant", lambda scientific_name, lang: None)

        factory = APIRequestFactory()
        req = factory.get(
            "/importPlant", data={"scientificName": "Unknown", "lang": "en"}
        )
        resp = view(req)

        assert resp.status_code == 404
        assert resp.data["error"] == "Plant not found"

    def test_importPlant_returns_500_on_exception(self, monkeypatch):
        mod = __import__(MODULE_PATH, fromlist=["importPlant"])
        view = mod.importPlant

        def boom(*args, **kwargs):
            raise RuntimeError("There's no API key for Perenual.")

        monkeypatch.setattr(mod, "getInfoPlant", boom)

        factory = APIRequestFactory()
        req = factory.get(
            "/importPlant", data={"scientificName": "Rosa canina", "lang": "en"}
        )
        resp = view(req)

        assert resp.status_code == 500
        assert "There's no API key for Perenual." in resp.data["error"]

    def test_importPlant_returns_200_with_payload(self, monkeypatch):
        mod = __import__(MODULE_PATH, fromlist=["importPlant"])
        view = mod.importPlant

        monkeypatch.setattr(
            mod,
            "getInfoPlant",
            lambda scientific_name, lang: {
                "scientificName": scientific_name,
                "commonName": "Rose",
                "family": "Rosaceae",
                "canFlower": True,
                "minTemperature": 2,
                "maxTemperature": 30,
                "description": "A plant",
            },
        )

        factory = APIRequestFactory()
        req = factory.get(
            "/importPlant", data={"scientificName": "Rosa canina", "lang": "en"}
        )
        resp = view(req)

        assert resp.status_code == 200
        assert resp.data["scientificName"] == "Rosa canina"
        assert resp.data["commonName"] == "Rose"
