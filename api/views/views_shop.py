from django.db import connection
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from api.models import Image, Plant, Shop


@require_GET
def get_shop(request):
    shop = Shop.get_solo()
    shop.initialize_starter_stock()

    seeds_with_info = []

    for scientific_name, price in shop.seeds.items():
        try:
            plant = Plant.objects.get(scientificName=scientific_name)
            image = Image.objects.filter(plant=plant).first()

            seeds_with_info.append(
                {
                    "scientificName": plant.scientificName,
                    "commonName": plant.commonName,
                    "family": plant.family,
                    "description": plant.description,
                    "price": price,
                    "image": image.url.url if image and image.url else None,
                }
            )
        except Plant.DoesNotExist:  # per si alguna llavor no esta a la bd de Plant
            continue

    return JsonResponse(
        {
            "seeds": seeds_with_info,
            "products": shop.products,
        },
        status=200,
    )
