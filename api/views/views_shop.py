import json

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from api.models import Inventory, Plant, Product, Shop, User
from api.serializer import ShopSeedSerializer


@require_GET
def get_shop(request):
    shop = Shop.get_solo()
    shop.initialize_starter_stock()

    seeds_data = []
    for scientific_name, price in shop.seeds.items():
        try:
            plant = Plant.objects.get(scientificName=scientific_name)
            seeds_data.append(
                {
                    "scientificName": plant.scientificName,
                    "commonName": plant.commonName,
                    "family": plant.family,
                    "description": plant.description,
                    "price": price,
                }
            )
        except Plant.DoesNotExist:
            continue

    products_data = []
    for product in Product.objects.only():
        products_data.append(
            {
                "name": product.name,
                "description": product.description,
                "effectType": product.effectType,
                "value": product.value,
                "durationHours": product.durationHours,
                "isInstant": product.isInstant,
                "price": product.price,
                "image_url": product.image_url.url if product.image_url else None,
                "rarity": product.rarity,
            }
        )

    return JsonResponse(
        {
            "seeds": ShopSeedSerializer(seeds_data, many=True).data,
            "products": products_data,
        },
        status=200,
    )


@csrf_exempt
@require_POST
def buy_item(request, username):
    user = get_object_or_404(User, username=username)
    inventory = get_object_or_404(Inventory, user=user)

    try:
        body = json.loads(request.body)
        item_type = body.get("type")
        item_name = body.get("name")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid body"}, status=400)

    if not item_type or not item_name:
        return JsonResponse({"error": "Missing 'type' or 'name'"}, status=400)

    shop = Shop.get_solo()

    if item_type == "seed":
        if item_name not in shop.seeds:
            return JsonResponse({"error": "Seed not found in shop"}, status=404)
        price = shop.seeds[item_name]

    elif item_type == "product":
        try:
            product = Product.objects.get(name=item_name)

        except Product.DoesNotExist:
            return JsonResponse({"error": "Product not found"}, status=404)

        price = product.price

    else:
        return JsonResponse(
            {"error": "Invalid type, must be 'seed' or 'product'"}, status=400
        )

    if inventory.coins < price:
        return JsonResponse({"error": "Not enough coins"}, status=400)

    inventory.coins -= price
    if item_type == "seed":
        inventory.seeds[item_name] = inventory.seeds.get(item_name, 0) + 1
    elif item_type == "product":
        inventory.products[item_name] = inventory.products.get(item_name, 0) + 1
    inventory.save()

    return JsonResponse(
        {
            "message": f"{item_type} '{item_name}' bought successfully",
            "coins_remaining": inventory.coins,
        },
        status=200,
    )
