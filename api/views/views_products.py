import json
from datetime import timedelta

from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from api.models import (
    ActiveProduct,
    MissionAction,
    MissionState,
    PlantInGarden,
    Pot,
    Product,
    User,
    UserMission,
)
from api.plant_simulation import apply_product


def update_user_missions(user, product_name):
    # Obtenim totes les missions en progres
    all_user_misions = UserMission.objects.filter(
        user=user, misssionState=MissionState.IN_PROGRESS
    )
    product = Product.objects.get(name=product_name)
    for mission in all_user_misions:
        if mission.mission.action == MissionAction.USE:
            if mission.mission.product is None or mission.mission.product == product:
                mission.current += 1
                if mission.mission.goal <= mission.current:
                    mission.missionState = MissionState.COMPLETED
                mission.save()


@csrf_exempt
@require_POST
def use_product(request):
    try:
        body = json.loads(request.body)
    except Exception:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    username = body.get("username")
    garden_name = body.get("garden_name")
    pot_number = body.get("pot_number")
    product_name = body.get("product_name")

    if not username or not garden_name or not pot_number or not product_name:
        return JsonResponse({"error": "Missing data"}, status=400)
    try:
        user = get_object_or_404(User, username=username)
        pot = get_object_or_404(
            Pot, garden__user=user, garden__name=garden_name, number=pot_number
        )
        plant = get_object_or_404(PlantInGarden, pot=pot)
        product = get_object_or_404(Product, name=product_name)

        apply_product(user, plant, product_name)
        update_user_missions(user, product_name)
        plant.refresh_from_db()

        response = {
            "status": "ok",
            "product": product.name,
            "isInstant": product.isInstant,
            "plant": {
                "health": plant.healthLevel,
                "water": plant.waterLevel,
                "growthPhase": plant.growthPhase,
            },
        }

        if not product.isInstant:
            active = ActiveProduct.objects.filter(plant=plant, product=product).latest(
                "applied_at"
            )

            applied_at = active.applied_at
            expires_at = applied_at + timedelta(hours=product.durationHours or 0)

            response.update(
                {
                    "durationHours": product.durationHours,
                    "appliedAt": applied_at.isoformat(),
                    "expiresAt": expires_at.isoformat(),
                }
            )

        return JsonResponse(response, status=200)

    except ActiveProduct.DoesNotExist:
        return JsonResponse({"error": "Active product not found"}, status=404)

    except Http404 as e:
        return JsonResponse({"error": str(e)}, status=404)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)
