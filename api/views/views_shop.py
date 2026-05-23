import json

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from api.models import Inventory, Plant, Product, Shop, User
from api.serializer import ShopSeedSerializer

from .views_translate import translate_text


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_shop(request):
    shop = Shop.get_solo()
    shop.initialize_starter_stock()
    lang = request.user.language

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

    for product in Product.objects.select_related().all():
        products_data.append(
            {
                "name": product.name,
                "displayName": translate_text(product.name, lang),
                "price": product.price,
                "image_url": product.image_url.url if product.image_url else None,
                "rarity": product.rarity,
            }
        )

    return JsonResponse(
        {
            "seeds": ShopSeedSerializer(
                seeds_data,
                many=True,
                context={"language": lang},
            ).data,
            "products": products_data,
        },
        status=200,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_shop_product(request, name):
    lang = request.user.language

    try:
        product = Product.objects.get(name=name)

    except Product.DoesNotExist:
        return JsonResponse(
            {"error": translate_text("Product not found", lang)},
            status=404,
        )

    data = {
        "name": product.name,
        "displayName": translate_text(
            product.name,
            lang,
        ),
        "description": translate_text(
            product.description,
            lang,
        ),
        "effectType": product.effectType,
        "value": product.value,
        "durationHours": product.durationHours,
        "isInstant": product.isInstant,
        "price": product.price,
        "rarity": product.rarity,
        "image_url": (product.image_url.url if product.image_url else None),
    }

    return JsonResponse(data, status=200)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_shop_seed(request, scientific_name):
    shop = Shop.get_solo()
    lang = request.user.language

    if scientific_name not in shop.seeds:
        return JsonResponse(
            {"error": translate_text("Seed not found in shop", lang)},
            status=404,
        )

    try:
        plant = Plant.objects.get(scientificName=scientific_name)

    except Plant.DoesNotExist:
        return JsonResponse(
            {"error": translate_text("Plant not found", lang)},
            status=404,
        )

    data = {
        "scientificName": plant.scientificName,
        "commonName": plant.commonName,
        "family": plant.family,
        "description": plant.description,
        "price": shop.seeds[scientific_name],
    }

    return JsonResponse(
        ShopSeedSerializer(
            data,
            context={"language": lang},
        ).data,
        status=200,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
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
        try:
            product = Product.objects.get(name=item_name)

        except Product.DoesNotExist:
            return JsonResponse(
                {"error": translate_text("Product not found", user.language)},
                status=404,
            )

        price = product.price
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
