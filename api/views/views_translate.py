import os

import requests
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


def translate_text(text: str | None, lang: str) -> str | None:
    if not text:
        return None

    api_key = os.getenv("GOOGLE_TRANSLATE_API_KEY")
    if not api_key:
        # if there's no key, returns the original text
        return text

    url = "https://translation.googleapis.com/language/translate/v2"
    params = {"q": text, "target": lang, "format": "text", "key": api_key}

    response = requests.post(url, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()
    return data["data"]["translations"][0]["translatedText"]


@api_view(["GET"])
@permission_classes([AllowAny])
def translate(request):
    text = request.query_params.get("text", None)
    lang = request.query_params.get("lang", None)
    try:
        if lang and text:
            text = translate_text(text, lang)
        else:
            return Response("error: There's no text neither language to translate", status=500)
    except Exception as e:
        return Response({"error": str(e)}, status=500)

    return Response(text)