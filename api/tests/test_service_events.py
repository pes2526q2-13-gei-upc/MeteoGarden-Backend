import pytest
import requests

from api.services.events import get_events_from_service


def test_get_events_no_api_key(monkeypatch):
    """Error si la clau d'API de l'entorn no està configurada."""
    monkeypatch.delenv("API_KEY_GRESCA", raising=False)
    with pytest.raises(RuntimeError, match="There's no API key for Gresca."):
        get_events_from_service()


def test_get_events_success(monkeypatch):
    """Retorna el JSON correcte si la petició HTTP té èxit."""
    monkeypatch.setenv("API_KEY_GRESCA", "test_key_123")

    class MockResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"events": [{"id": "evt_1", "title": "Gresca Planta"}]}

    def mock_get(url, headers, timeout):
        assert headers["Authorization"] == "Token test_key_123"
        return MockResponse()

    monkeypatch.setattr(requests, "get", mock_get)

    data = get_events_from_service()
    assert "events" in data
    assert data["events"][0]["title"] == "Gresca Planta"


def test_get_events_exception(monkeypatch):
    """Si falla la connexió, no llença excepció sinó que fa un log i retorna None."""
    monkeypatch.setenv("API_KEY_GRESCA", "test_key_123")

    def mock_get_fail(*args, **kwargs):
        raise requests.exceptions.RequestException("Timeout de connexió")

    monkeypatch.setattr(requests, "get", mock_get_fail)

    # Com que el codi té un 'except Exception' que fa log, hauria de retornar None de forma segura
    res = get_events_from_service()
    assert res is None
