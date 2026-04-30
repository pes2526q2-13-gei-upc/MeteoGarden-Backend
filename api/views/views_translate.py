import os
from typing import Any

import requests
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


def translate_text(
    texts: str | list | None, lang: str
) -> list[Any] | None | str | list:
    if not texts:
        return None

    api_key = os.getenv("GOOGLE_TRANSLATE_API_KEY")
    if not api_key:
        # if there's no key, returns the original text
        return texts

    is_single_text = isinstance(texts, str)
    texts_list = [texts] if is_single_text else texts
    url = "https://translation.googleapis.com/language/translate/v2"
    params = [("q", t) for t in texts_list if t]
    params.append(("target", lang))
    params.append(("key", api_key))
    params.append(("format", "text"))

    response = requests.post(url, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    translations = [t["translatedText"] for t in data["data"]["translations"]]
    return translations[0] if is_single_text else translations


@api_view(["GET"])
@permission_classes([AllowAny])
def translate(request):
    text = request.query_params.get("text", None)
    lang = request.query_params.get("lang", None)
    if not text or not lang:
        return Response({"error": "No text or language provided"}, status=400)

    text_to_send = text[0] if len(text) == 1 else text
    try:
        text = translate_text(text_to_send, lang)
    except Exception as e:
        return Response({"error": str(e)}, status=500)

    return Response(text)
