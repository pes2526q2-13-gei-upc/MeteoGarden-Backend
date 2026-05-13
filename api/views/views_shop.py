import json

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from views_translate import translate_text

from api.models import Inventory, Plant, Product, Shop, User
from api.serializer import ShopSeedSerializer


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_shop(request):
    user = request.user
    lang = user.language

    shop = Shop.get_solo()
    shop.initialize_starter_stock()

    seeds_data = []
    for scientific_name, price in shop.seeds.items():
        try:
            plant = Plant.objects.get(scientificName=scientific_name)
            seeds_data.append(
                {
                    "scientificName": plant.scientificName,
                    "commonName": translate_text(plant.commonName, lang),
                    "family": plant.family,
                    "description": translate_text(plant.description, lang),
                    "price": price,
                }
            )
        except Plant.DoesNotExist:
            continue

    products_data = []
    for name, price in shop.products.items():
        try:
            product = Product.objects.get(name=name)
            products_data.append(
                {
                    "name": translate_text(
                        product.name,
                        lang,
                    ),
                    "description": translate_text(
                        product.description,
                        lang,
                    ),
                    "effectType": translate_text(
                        product.effectType,
                        lang,
                    ),
                    "value": product.value,
                    "durationHours": product.durationHours,
                    "isInstant": product.isInstant,
                    "price": price,
                    "image_url": product.image_url.url if product.image_url else None,
                }
            )
        except Product.DoesNotExist:
            continue

    return JsonResponse(
        {
            "seeds": ShopSeedSerializer(
                seeds_data,
                many=True,
                context={"request": request},
            ).data,
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
        return JsonResponse(
            {"error": translate_text("Invalid body", user.language)}, status=400
        )

    if not item_type or not item_name:
        return JsonResponse(
            {"error": translate_text("Missing 'type' or 'name'", user.language)},
            status=400,
        )

    shop = Shop.get_solo()

    if item_type == "seed":
        if item_name not in shop.seeds:
            return JsonResponse(
                {"error": translate_text("Seed not found in shop", user.language)},
                status=404,
            )
        price = shop.seeds[item_name]

    elif item_type == "product":
        if item_name not in shop.products:
            return JsonResponse(
                {"error": translate_text("Product not found in shop", user.language)},
                status=404,
            )
        price = shop.products[item_name]

    else:
        return JsonResponse(
            {
                "error": translate_text(
                    "Invalid type, must be 'seed' or 'product'", user.language
                )
            },
            status=400,
        )

    if inventory.coins < price:
        return JsonResponse(
            {"error": translate_text("Not enough coins", user.language)}, status=400
        )

    inventory.coins -= price
    if item_type == "seed":
        inventory.seeds[item_name] = inventory.seeds.get(item_name, 0) + 1
    elif item_type == "product":
        inventory.products[item_name] = inventory.products.get(item_name, 0) + 1
    inventory.save()

    translated_item_type = translate_text(item_type, user.language)
    translated_item_name = translate_text(item_name, user.language)

    success_message = translate_text(
        f"{translated_item_type} '{translated_item_name}' bought successfully",
        user.language,
    )

    return JsonResponse(
        {
            "message": success_message,
            "coins_remaining": inventory.coins,
        },
        status=200,
    )
