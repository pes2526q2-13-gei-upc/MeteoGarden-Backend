import os

import requests
from django.contrib.auth import authenticate
from django.utils import timezone
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from ..models import Garden, Inventory, Mission, MissionState, Pot, User, UserMission
from .views_translate import translate_text

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")


def assignAllMissions(user):
    missions = Mission.objects.all()
    for mission in missions:
        UserMission.objects.create(
            user=user,
            mission=mission,
            missionState=MissionState.IN_PROGRESS,
            acquiredAt=timezone.now(),
        )


def verify_google_token(token_str):
    if token_str.startswith("eyJ"):
        try:
            info = id_token.verify_oauth2_token(
                token_str,
                google_requests.Request(),
                GOOGLE_CLIENT_ID,
            )
            return info
        except ValueError:
            raise ValueError("ID Token inválido")

    else:
        response = requests.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            params={"access_token": token_str},
        )

        if response.status_code != 200:
            raise ValueError("Access Token inválido o expirado")

        info = response.json()

        return info


# Create your views here.
@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    return Response({"health status": "ok"})


# Register view
@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):

    # Check if the garden name isn't empty
    garden_name = request.data.get("gardenName")
    if not garden_name:
        return Response({"error": "Garden name is mandatory"}, status=400)

    user = User.objects.create_user(
        username=request.data["username"],
        password=request.data["password"],
        email=request.data["email"],
        city=request.data["city"],
        language=request.data["language"],
        numPlantsCollected=0,
        stationCode=request.data["stationCode"],
    )
    assignAllMissions(user)

    # Create the inventory
    Inventory.objects.create(user=user)

    # Create the garden and the pots
    garden = Garden.objects.create(user=user, name=garden_name)
    pots_to_create = []
    for i in range(1, 17):  # To create 16 pots (from 1 to 16)
        pots_to_create.append(Pot(garden=garden, number=i))

    # bulk_create is faster than create a single object
    Pot.objects.bulk_create(pots_to_create)

    token, created = Token.objects.get_or_create(user=user)
    return Response(
        {
            "token": token.key,
            "message": translate_text(
                "User, garden and inventory created", user.language
            ),
        }
    )


# Login view
@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    username = request.data["username"]
    password = request.data["password"]

    lang = "en"

    existing_user = User.objects.filter(username=username).first()
    if existing_user:
        lang = existing_user.language

    user = authenticate(username=username, password=password)
    if user:
        token, created = Token.objects.get_or_create(user=user)
        return Response(
            {
                "token": token.key,
                "username": user.username,
                "message": translate_text("Login correcte", lang),
            }
        )
    return Response({"error": translate_text("Wrong credentials", lang)}, status=400)


# View profile
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_profile(request):
    user = request.user
    inventory = Inventory.objects.get(user=user)
    gardens = Garden.objects.filter(user=user)  # We use filter to get all gardens
    return Response(
        {
            "username": user.username,
            "email": user.email,
            "city": user.city,
            "stationCode": user.stationCode,
            "language": user.language,
            "lastEntry": user.lastEntry,
            "numPlantsCollected": user.numPlantsCollected,
            "numCoins": inventory.coins,
            "gardens": [{"gardenName": garden.name} for garden in gardens],
        }
    )


# Edit profile
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def edit_profile(request):
    user = request.user
    data = request.data
    user.email = data.get("email", user.email)
    user.city = data.get("city", user.city)
    user.language = data.get("language", user.language)
    user.numPlantsCollected = data.get("numPlantsCollected", user.numPlantsCollected)
    user.stationCode = data.get("stationCode", user.stationCode)
    if "password" in data:
        user.set_password(data["password"])
    try:
        user.save()
        return Response(
            {"message": translate_text("Actualized profile", user.language)}
        )
    except Exception as e:
        return Response({"error": translate_text(str(e), user.language)}, status=400)


@api_view(["POST"])
@permission_classes([AllowAny])
def google_verify(request):

    # Verifiquem si l'usuari de google ja existeix a la base de dades:
    token_str = request.data.get("id_token")
    if not token_str:
        return Response({"error": "id_token is required"}, status=400)

    try:
        info = verify_google_token(token_str)
    except ValueError:
        return Response({"error": "Invalid Google token"}, status=400)

    google_id = info["sub"]
    email = info["email"]
    name = info.get("name", "")

    user = User.objects.filter(google_id=google_id).first()
    if not user:
        user = User.objects.filter(email=email).first()

    if user:
        # L'usuari existeix
        token, _ = Token.objects.get_or_create(user=user)
        return Response(
            {
                "exists": True,
                "token": token.key,
                "username": user.username,
            }
        )
    else:
        # L'usuari no existeix, per tant ha de registrar-se
        return Response(
            {
                "exists": False,
                "email": email,
                "name": name,
            }
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def google_register(request):
    # Agafem el token de google
    token_str = request.data.get("id_token")
    if not token_str:
        return Response({"error": "id_token is required"}, status=400)

    # Verifiquem si existeix el compte de google
    try:
        info = verify_google_token(token_str)
    except ValueError:
        return Response({"error": "Invalid Google token"}, status=400)

    google_id = info["sub"]
    email = info["email"]

    if User.objects.filter(google_id=google_id).exists():
        return Response(
            {"error": "User already exists, use /auth/google/verify"}, status=400
        )
    if User.objects.filter(email=email).exists():
        return Response({"error": "Email already registered"}, status=400)

    # Comprovem que existeixen els camps obligatoris
    username = request.data.get("username")
    city = request.data.get("city")
    language = request.data.get("language")
    station_code = request.data.get("stationCode")
    garden_name = request.data.get("gardenName")

    if not all([username, city, language, station_code, garden_name]):
        return Response(
            {
                "error": "username, city, language, stationCode and gardenName are required"
            },
            status=400,
        )

    if User.objects.filter(username=username).exists():
        return Response(
            {"error": translate_text("Username already taken", language)}, status=400
        )

    # Es crea l'usuari sense contrasenya
    user = User.objects.create_user(
        username=username,
        email=email,
        password=None,  # Sense contrasenya
        google_id=google_id,
        city=city,
        language=language,
        stationCode=station_code,
        numPlantsCollected=0,
    )
    assignAllMissions(user)

    # Reutilitzem el codi de register:
    # Create the inventory
    Inventory.objects.create(user=user)

    # Create the garden and the pots
    garden = Garden.objects.create(user=user, name=garden_name)
    pots_to_create = []
    for i in range(1, 17):  # To create 16 pots (from 1 to 16)
        pots_to_create.append(Pot(garden=garden, number=i))

    # bulk_create is faster than create a single object
    Pot.objects.bulk_create(pots_to_create)

    token, created = Token.objects.get_or_create(user=user)

    return Response(
        {
            "token": token.key,
            "username": user.username,
            "message": translate_text("User created successfully", language),
        }
    )


# Register view
@api_view(["DELETE"])
@permission_classes(
    [IsAuthenticated]
)  # Aqui s'envia el token i llavors django associa el token a l'usuari
def delete_profile(request):
    lang = request.user.language
    request.user.delete()  # eliminem l'usuari i, per casacada, s'eliminen les clases associades
    return Response({"message": translate_text("User deleted successfully", lang)})


# Validate token
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def validate_token(request):
    # Si la crida no dona error, llavors el token és correcte
    return Response({"valid": True, "username": request.user.username})
