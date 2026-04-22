import os

import requests
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


def getEventsFromService() -> dict:
    key = os.getenv("API_KEY_GRESCA")
    if not key:
        raise RuntimeError("There's no API key for Gresca.")

    try:
        print("hola")
        url = "https://gresca.jaumelopez.dev/api/external/events/dataset-20260325025"
        headers = {"Authorization": f"Token {key}", "Content-Type": "application/json"}
        # params = {"city": "tarragona"}
        response = requests.get(url, headers=headers)
        print(response.status_code)
        response.raise_for_status()

        data = response.json()
        return data

    except Exception:
        return None


@api_view(["GET"])
@permission_classes([AllowAny])
def events(request):
    event = getEventsFromService()
    print(event)
    return Response({"events": event})
