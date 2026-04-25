import json
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST
from datetime import timedelta
from django.views.decorators.csrf import csrf_exempt
from api.models import PlantInGarden, ActiveProduct, Product, User
from api.plant_simulation import apply_product

@csrf_exempt
@require_POST
def use_product(request):
    body = json.loads(request.body)

    username = body.get("username")
    pot_id = body.get("pot_id")
    product_name = body.get("product_name")

    if not pot_id or not product_name:
        return JsonResponse({"error": "Missing data"}, status=400)

    try:
        user = get_object_or_404(User, username=username)
        plant = PlantInGarden.objects.get(
            pot__id=pot_id,
            pot__garden__user=user
        )
        product = Product.objects.get(name=product_name)

        apply_product(user, plant, product_name)
        plant.refresh_from_db()

        response = {
            "status": "ok",
            "product": product.name,
            "isInstant": product.isInstant,
            "plant": {
                "health": plant.healthLevel,
                "water": plant.waterLevel,
                "growthPhase": plant.growthPhase,
            }
        }

        if not product.isInstant:
            active = ActiveProduct.objects.filter(
                plant=plant,
                product=product
            ).latest("applied_at")

            applied_at = active.applied_at
            expires_at = applied_at + timedelta(hours=product.durationHours or 0)

            response.update({
                "durationHours": product.durationHours,
                "appliedAt": applied_at.isoformat(),
                "expiresAt": expires_at.isoformat(),
            })

        return JsonResponse(response)

    except PlantInGarden.DoesNotExist:
        return JsonResponse({"error": "Plant not found"}, status=404)

    except Product.DoesNotExist:
        return JsonResponse({"error": "Product not found"}, status=404)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)