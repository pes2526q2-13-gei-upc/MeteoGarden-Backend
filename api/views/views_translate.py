from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from api.services.translate import translate_text


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
