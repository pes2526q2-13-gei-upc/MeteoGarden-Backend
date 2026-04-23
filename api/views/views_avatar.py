from rest_framework.decorators import api_view, permission_classes
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from api.models import Avatar, User
from config.settings import MEDIA_URL


def getImages():
    return {
        "accessories": [
            {"id": i, "url": f"{MEDIA_URL}/avatar/accessories/{i}.png"}
            for i in range(1, 6)
        ],
        "body": [
            {"id": i, "url": f"{MEDIA_URL}/avatar/body/{i}.png"} for i in range(1, 5)
        ],
        "clothing": [
            {"id": i, "url": f"{MEDIA_URL}/avatar/clothing/{i}.png"}
            for i in range(1, 8)
        ],
        "eye": [
            {"id": i, "url": f"{MEDIA_URL}/avatar/eye/{i}.png"} for i in range(1, 9)
        ],
        "expression": {
            "happy": [{"id": 0, "url": f"{MEDIA_URL}/avatar/expression/happy/0.png"}],
            "sad": [
                {"id": i, "url": f"{MEDIA_URL}/avatar/expression/sad/{i}.png"}
                for i in range(1, 5)
            ],
            "shivering": [
                {"id": i, "url": f"{MEDIA_URL}/avatar/expression/shivering/{i}.png"}
                for i in range(1, 5)
            ],
            "sweating": [
                {"id": 0, "url": f"{MEDIA_URL}/avatar/expression/sweating/0.png"}
            ],
            "wet": [{"id": 0, "url": f"{MEDIA_URL}/avatar/expression/wet/0.png"}],
        },
        "hair": {
            color: [
                {"id": i, "url": f"{MEDIA_URL}/avatar/hair/{color}/{i}.png"}
                for i in range(1, 9)
            ]
            for color in ["blond", "brown", "dark"]
        },
        "facialHair": {
            color: [{"id": 1, "url": f"{MEDIA_URL}/avatar/facialHair/1/{color}.png"}]
            for color in ["blond", "brown", "dark"]
        },
    }


@api_view(["GET"])
@permission_classes([AllowAny])
def avatar(request):
    return Response(getImages())


@api_view(["GET"])
@permission_classes([AllowAny])
def getUserAvatar(request, username):

    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return Response({"user": "User not found."}, status=404)

    avatar = get_object_or_404(Avatar, user=user)

    data = {
        "accessories": f"{MEDIA_URL}/avatar/accessories/{avatar.accessories}.png",
        "body": f"{MEDIA_URL}/avatar/body/{avatar.body}.png",
        "clothing": f"{MEDIA_URL}/avatar/clothing/{avatar.clothing}.png",
        "eye": f"{MEDIA_URL}/avatar/eye/{avatar.eye}.png",
        "expression": f"{MEDIA_URL}/avatar/expression/{avatar.expression}/{avatar.expression_variant}.png",
        "hair": f"{MEDIA_URL}/avatar/hair/{avatar.hair_color}/{avatar.hair_style}.png",
        "facialHair": f"{MEDIA_URL}/avatar/facialHair/{avatar.facial_hair}/{avatar.facial_hair_color}.png",
    }

    return Response(data)


@api_view(["POST", "PUT"])
def saveAvatar(request, username):
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return Response({"error": "User not found."}, status=404)

    avatar, created = Avatar.objects.get_or_create(user=user)

    avatar.accessories = request.data.get("accessories", avatar.accessories)
    avatar.body = request.data.get("body", avatar.body)
    avatar.clothing = request.data.get("clothing", avatar.clothing)
    avatar.eye = request.data.get("eye", avatar.eye)
    avatar.expression = request.data.get("expression", avatar.expression)
    avatar.expression_variant = request.data.get(
        "expression_variant", avatar.expression_variant
    )
    avatar.hair_color = request.data.get("hair_color", avatar.hair_color)
    avatar.hair_style = request.data.get("hair_style", avatar.hair_style)
    avatar.facial_hair = request.data.get("facial_hair", avatar.facial_hair)
    avatar.facial_hair_color = request.data.get(
        "facial_hair_color", avatar.facial_hair_color
    )

    avatar.save()

    data = {
        "accessories": f"{MEDIA_URL}/avatar/accessories/{avatar.accessories}.png",
        "body": f"{MEDIA_URL}/avatar/body/{avatar.body}.png",
        "clothing": f"{MEDIA_URL}/avatar/clothing/{avatar.clothing}.png",
        "eye": f"{MEDIA_URL}/avatar/eye/{avatar.eye}.png",
        "expression": f"{MEDIA_URL}/avatar/expression/{avatar.expression}/{avatar.expression_variant}.png",
        "hair": f"{MEDIA_URL}/avatar/hair/{avatar.hair_color}/{avatar.hair_style}.png",
        "facialHair": f"{MEDIA_URL}/avatar/facialHair/{avatar.facial_hair}/{avatar.facial_hair_color}.png",
    }

    return Response(data, status=201 if created else 200)
