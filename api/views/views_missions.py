from gunicorn.dirty.stash import exists
from rest_framework.decorators import permission_classes, api_view
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.response import Response
from ..models import Mission, UserMission, Plant

# Get missions
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def getUserMissions(request):
    missions = UserMission.objects.filter(user=request.user)
    return Response({"missions": [{
        "Name": mission.name,
        "Description": mission.description,
        "Plant reward common name": mission.seed.commonName,
        "Plant reward scientific name": mission.seed.scientificName,
        "Reward coins": mission.rewardCoins,
        "Mission state": mission.missionState,
        "acquired at": mission.acquiredAt,
    } for mission in missions]})

# Create mission
@api_view(["POST"])
@permission_classes([AllowAny])
def createMission(request):
    # Check the mandatory fields
    name = request.data.get("name")
    description = request.data.get("description")
    seed = request.data.get("seed")
    rewardCoins = request.data.get("rewardCoins")
    product = request.data.get("product")

    if not all([name, description, seed, rewardCoins, product]):
        return Response(
            {
                "error": "name, description, seed, rewardCoins and product are required fields"
            },
            status=400,
        )
    if not Plant.objects.filter(name=name).exists():
        return Response(
            {
                "error": f"Plant with scientific name '{seed}' does not exist"
            },
            status=400,
        )
    plant = Plant.objects.get(name=name)
    Mission.objects.create(
        name=name,
        description=description,
        seed=plant,
        rewardCoins=int(rewardCoins),
        product=product,
    )
    return Response(
        "Mission created successfully",
    )
