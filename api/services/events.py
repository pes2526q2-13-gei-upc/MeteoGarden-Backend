import os

import requests

from api.services.xema_sync import logger


def getEventsFromService(url=None) -> dict:
    key = os.getenv("API_KEY_GRESCA")
    if not key:
        raise RuntimeError("There's no API key for Gresca.")
    if not url:
        url = "https://gresca.jaumelopez.dev/api/external/events"
    try:
        headers = {"Authorization": f"Token {key}", "Content-Type": "application/json"}
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        return response.json()

    except Exception as e:
        logger.error(f"Error getting events: {e}")
