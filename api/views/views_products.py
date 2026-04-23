from django.http import JsonResponse
from django.views.decorators.http import require_POST

from api.models import PlantInGarden
from api.plant_simulation import apply_product


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

        return JsonResponse({"status": "ok"})

    except PlantInGarden.DoesNotExist:
        return JsonResponse({"error": "Plant not found"}, status=404)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)
