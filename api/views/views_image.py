import os
import urllib

import requests
from django.core.files.base import ContentFile
from rest_framework.decorators import api_view
from rest_framework.response import Response

from config.settings import MEDIA_URL

from ..models import AlbumEntry, GrowthState, Image, Plant, User

POLLINATIONS_URL = "https://gen.pollinations.ai/image"
STATE_DESCRIPTIONS = {
    "seed": "a single small round brown seed, surface texture detailed",
    "germination": "tiny green sprout emerging from a seed, two small cotyledon leaves, delicate stem",
    "growth": "young plant, vibrant green leaves, developing stem, bushy and healthy growth",
    "mature": "full-grown plant, lush foliage, complex leaf structure, thick sturdy stem, vigorous appearance",
    "flowering": "fully mature plant with vibrant blooming flowers, petals visible, healthy foliage",
    "dead": "withered and dried plant, brown and yellow shriveled leaves, drooping stem, brittle texture, decaying appearance",
}


def createPlantImages(scientificName):
    from rembg import remove

    safe_name = scientificName.replace(" ", "_").lower()
    plant = Plant.objects.get(scientificName=scientificName)
    if not plant:
        return Response({"plant": "Plant not found."}, status=404)

    api_key = os.getenv("POLLINATION_API_KEY")

    style = f"""
        game-ready 2D farming game asset,
        isolated object cutout on pure transparent background,
        front-facing orthographic view,
        centered composition,
        clean sharp edges, no blur,
        botanically accurate {scientificName} characteristics,
        stem and leaves only,
        NO pot, NO container, NO soil, NO ground, NO shadow, NO surface,
        bright vibrant colors, soft cel-shaded cartoon style,
        high quality digital art, PNG format,
        clean alpha channel
        """.strip()

    for state_value, state_label in GrowthState.choices:
        state_desc = STATE_DESCRIPTIONS.get(state_value, state_label)

        prompt = f"{state_desc}, {style}"
        encoded_prompt = urllib.parse.quote(prompt)
        image_url = f"{POLLINATIONS_URL}/{encoded_prompt}?model=flux"

        response = requests.get(
            image_url, headers={"Authorization": f"Bearer {api_key}"}, timeout=60
        )

        if response.status_code == 200:
            transparent_image_bytes = remove(response.content)
            image_content = ContentFile(transparent_image_bytes)

            new_image = Image(plant=plant, growthPhase=state_value)

            filename = f"{safe_name}_{state_value}.png"
            new_image.url.save(filename, image_content, save=True)

    return None


@api_view(["GET"])
def getUserAlbum(request, username):
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return Response({"user": "User not found."}, status=404)

    list_of_albums = AlbumEntry.objects.filter(user=user).select_related("plant")

    list = []
    for album in list_of_albums:
        image = Image.objects.filter(uploader=user, plant=album.plant).first()
        if image and image.url:
            list.append(
                {
                    "name": album.plant.scientificName,
                    "image": image.url.url,
                }
            )

    return Response(list)


@api_view(["GET"])
def getPlantImage(request):
    scientificName = request.query_params.get("plant")
    if not scientificName:
        return Response({"plant": "Plant not found."}, status=404)
    state = request.query_params.get("state")
    if not state:
        return Response({"state": "State not found."}, status=404)
    plant = Plant.objects.get(scientificName=scientificName)

    image = Image.objects.filter(plant=plant, growthPhase=state).first()
    if not image:
        return Response({"plant": "Plant not found."}, status=404)

    return MEDIA_URL + image.url.url
