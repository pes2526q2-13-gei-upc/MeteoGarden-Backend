import pytest
from rest_framework.test import APIRequestFactory

# Ajusta aquest import al path real del teu projecte:
# ex: from api.views.views_translate import translate_text, translate
from api.views.views_translate import translate, translate_text


class DummyResponse:
    def __init__(self, status_code=200, payload=None, raise_for_status_exc=None):
        self.status_code = status_code
        self._payload = payload or {}
        self._exc = raise_for_status_exc

    def raise_for_status(self):
        if self._exc:
            raise self._exc

    def json(self):
        return self._payload


@pytest.mark.django_db
class TestTranslateText:
    def test_translate_text_returns_none_when_text_none_or_empty(self, monkeypatch):
        assert translate_text(None, "ca") is None
        assert translate_text("", "ca") is None

    def test_translate_text_no_api_key_returns_original_text(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_TRANSLATE_API_KEY", raising=False)
        assert translate_text("Hello", "ca") == "Hello"

    def test_translate_text_calls_google_and_returns_translated(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_TRANSLATE_API_KEY", "fake-key")

        def fake_post(url, params=None, timeout=None):
            assert url == "https://translation.googleapis.com/language/translate/v2"
            assert params["q"] == "Hello"
            assert params["target"] == "ca"
            assert params["format"] == "text"
            assert params["key"] == "fake-key"
            assert timeout == 30

            return DummyResponse(
                payload={
                    "data": {"translations": [{"translatedText": "Hola"}]},
                }
            )

        # IMPORTANT: mockeja requests.post al mòdul on està definit translate_text
        import api.views.views_translate as mod

        monkeypatch.setattr(mod.requests, "post", fake_post)

        assert translate_text("Hello", "ca") == "Hola"

    def test_translate_text_raises_if_google_errors(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_TRANSLATE_API_KEY", "fake-key")

        import api.views.views_translate as mod

        def fake_post(url, params=None, timeout=None):
            return DummyResponse(raise_for_status_exc=RuntimeError("boom"))

        monkeypatch.setattr(mod.requests, "post", fake_post)

        with pytest.raises(RuntimeError, match="boom"):
            translate_text("Hello", "ca")


@pytest.mark.django_db
class TestTranslateEndpoint:
    def test_translate_endpoint_missing_params_returns_500(self):
        factory = APIRequestFactory()
        request = factory.get("/translate")
        resp = translate(request)

        assert resp.status_code == 500
        assert resp.data == "error: There's no text neither language to translate"

    def test_translate_endpoint_ok_returns_translated_text(self, monkeypatch):
        import api.views.views_translate as mod

        monkeypatch.setattr(mod, "translate_text", lambda text, lang: "Hola")

        factory = APIRequestFactory()
        request = factory.get("/translate", {"text": "Hello", "lang": "ca"})
        resp = translate(request)

        assert resp.status_code == 200
        assert resp.data == "Hola"

    def test_translate_endpoint_translate_text_exception_returns_500(self, monkeypatch):
        import api.views.views_translate as mod

        def boom(text, lang):
            raise RuntimeError("translator down")

        monkeypatch.setattr(mod, "translate_text", boom)

        factory = APIRequestFactory()
        request = factory.get("/translate", {"text": "Hello", "lang": "ca"})
        resp = translate(request)

        assert resp.status_code == 500
        assert resp.data["error"] == "translator down"
