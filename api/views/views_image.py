import os
import urllib

import requests
from django.core.files.base import ContentFile
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ..models import AlbumEntry, GrowthState, Image, Plant, User

POLLINATIONS_URL = "https://gen.pollinations.ai/image"


def createPlantImages(scientificName):

    safe_name = urllib.parse.quote(scientificName)
    plant = Plant.objects.get(scientificName=scientificName)
    if not plant:
        return Response({"plant": "Plant not found."}, status=404)

    api_key = os.getenv("POLLINATION_API_KEY")

    style = f"""
        game-ready 2D farming game sprite of a {scientificName} plant,
        recognizable real-world characteristics of {scientificName},
        botanically distinguishable silhouette,
        stem, leaves and flowers only,
        only the plant visible,
        no pot, no flower pot, no planter, no container,
        no soil, no dirt, no ground, no base tile, no surface,
        no shadow underneath, no table,
        floating plant, isolated object cutout, sticker-like sprite,
        clean cut edges,
        transparent background, PNG with alpha channel,
        centered composition,
        bright vibrant colors,
        soft cartoon shading,
        no realistic photo, no background scene, no environment, no decoration,
        no text, no watermark
        """.strip()

    for state_value, state_label in GrowthState.choices:

        prompt = f"{safe_name} plant, {state_label} stage, {style}"
        encoded_prompt = urllib.parse.quote(prompt)
        image_url = f"{POLLINATIONS_URL}/{encoded_prompt}?model=flux"

        response = requests.get(
            image_url, headers={"Authorization": f"Bearer {api_key}"}, timeout=60
        )

        if response.status_code == 200:
            image_content = ContentFile(response.content)

            new_image = Image(plant=plant)

            filename = f"{safe_name}_{state_value}.png"
            new_image.url.save(filename, image_content, save=True)

    return None


@api_view(["GET"])
def getUserAlbum(request):

    username = request.query_params.get("username")
    if not username:
        return Response({"username": "This query param is required."}, status=400)

    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return Response({"user": "User not found."}, status=404)

    list_of_albums = AlbumEntry.objects.filter(user=user).select_related("plant")

    list_url = []
    for album in list_of_albums:
        image = Image.objects.filter(plant=album.plant).first()
        if image and image.url:
            list_url.append(image.url.url)

    return Response(list_url)
