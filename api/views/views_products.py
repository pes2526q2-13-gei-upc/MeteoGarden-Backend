from django.http import JsonResponse
from django.views.decorators.http import require_POST

from api.models import MissionAction, MissionState, PlantInGarden, Product, UserMission
from api.plant_simulation import apply_product


def updateUseMissions(user, productName):
    # Obtenim totes les missions en progres
    allUserMisions = UserMission.objects.filter(
        user=user, misssionState=MissionState.IN_PROGRESS
    )
    product = Product.objects.get(name=productName)
    for mission in allUserMisions:
        if mission.mission.action == MissionAction.USE:
            if mission.mission.product is None or mission.mission.product == product:
                mission.current += 1
                if mission.mission.goal <= mission.current:
                    mission.missionState = MissionState.COMPLETED
                mission.save()


@require_POST
def use_product(request):
    user = request.user
    pot_id = request.POST.get("pot_id")
    product_name = request.POST.get("product_name")

    if not pot_id or not product_name:
        return JsonResponse({"error": "Missing data"}, status=400)

    try:
        plant = PlantInGarden.objects.get(pot__id=pot_id, pot__garden__user=user)
        apply_product(user, plant, product_name)
        updateUseMissions(user, product_name)

        return JsonResponse({"status": "ok"})

    except PlantInGarden.DoesNotExist:
        return JsonResponse({"error": "Plant not found"}, status=404)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)
