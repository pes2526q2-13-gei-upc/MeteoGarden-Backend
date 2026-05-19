from datetime import timedelta

from rest_framework import serializers

from api.models import ActiveProduct, Event, EventsCategory, Image, Plant, Pot, Product
from api.views.views_translate import translate_text


class PotSerializer(serializers.ModelSerializer):
    plant = serializers.SerializerMethodField()
    growth_phase = serializers.SerializerMethodField()
    health_level = serializers.SerializerMethodField()
    water_level = serializers.SerializerMethodField()
    planted_at = serializers.SerializerMethodField()
    last_watered_at = serializers.SerializerMethodField()

    class Meta:
        model = Pot
        fields = [
            "pot_number",
            "occupied",
            "plant",
            "growth_phase",
            "health_level",
            "water_level",
            "planted_at",
            "last_watered_at",
        ]

    pot_number = serializers.IntegerField(source="number")

    def get_plant(self, obj):
        planting = getattr(obj, "plantingarden", None)
        if planting is None:
            return None

        request = self.context.get("request")
        lang = request.GET.get("lang", "en") if request else "en"

        image = Image.objects.filter(
            plant=planting.plant, growthPhase=planting.growthPhase
        ).first()
        image_url = image.url.url if image and image.url else None

        active_products = [
            {
                "name": active_product.product.name,
                "displayName": translate_text(active_product.product.name, lang),
                "applied_at": active_product.applied_at.isoformat(),
                "expires_at": (
                    active_product.applied_at
                    + timedelta(hours=active_product.product.durationHours)
                ).isoformat(),
            }
            for active_product in ActiveProduct.objects.filter(
                plant=planting
            ).select_related("product")
            if active_product.is_active()
        ]
        return {
            "scientific_name": planting.plant.scientificName,
            "common_name": translate_text(planting.plant.commonName, lang),
            "family": planting.plant.family,
            "can_flower": planting.plant.canFlower,
            "min_temperature": planting.plant.minTemperature,
            "max_temperature": planting.plant.maxTemperature,
            "image_url": image_url,
            "active_products": active_products,
        }

    def get_growth_phase(self, obj):
        planting = getattr(obj, "plantingarden", None)
        return planting.growthPhase if planting else None

    def get_health_level(self, obj):
        planting = getattr(obj, "plantingarden", None)
        return planting.healthLevel if planting else None

    def get_water_level(self, obj):
        planting = getattr(obj, "plantingarden", None)
        return planting.waterLevel if planting else None

    def get_planted_at(self, obj):
        planting = getattr(obj, "plantingarden", None)
        return (
            planting.plantedAt.isoformat() if planting and planting.plantedAt else None
        )

    def get_last_watered_at(self, obj):
        planting = getattr(obj, "plantingarden", None)
        return (
            planting.lastWateredAt.isoformat()
            if planting and planting.lastWateredAt
            else None
        )


class InventorySeedSerializer(serializers.Serializer):
    scientificName = serializers.CharField()
    amount = serializers.IntegerField()
    image_url = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()

    def get_plant(self, obj):
        scientific_name = obj.get("scientificName")

        try:
            return Plant.objects.get(scientificName=scientific_name)
        except Plant.DoesNotExist:
            return None

    def get_image_url(self, obj):
        plant = self.get_plant(obj)
        if not plant:
            return None
        image = Image.objects.filter(plant=plant, growthPhase="mature").first()
        return image.url.url if image and image.url else None

    def get_description(self, obj):
        plant = self.get_plant(obj)
        return plant.description if plant else None


class ShopSeedSerializer(serializers.Serializer):
    scientificName = serializers.CharField()
    commonName = serializers.SerializerMethodField()
    family = serializers.CharField()
    description = serializers.SerializerMethodField()
    price = serializers.IntegerField()
    image_url = serializers.SerializerMethodField()

    def get_commonName(self, obj):
        request = self.context.get("request")
        lang = request.GET.get("lang", "en") if request else "en"
        common_name = obj.get("commonName", "")
        return translate_text(common_name, lang)

    def get_description(self, obj):
        request = self.context.get("request")
        lang = request.GET.get("lang", "en") if request else "en"
        description = obj.get("description", "")
        return translate_text(description, lang)

    def get_image_url(self, obj):
        scientific_name = obj.get("scientificName")
        try:
            plant = Plant.objects.get(scientificName=scientific_name)
        except Plant.DoesNotExist:
            return None
        image = Image.objects.filter(plant=plant, growthPhase="seed").first()
        return image.url.url if image and image.url else None


class InventoryProductSerializer(serializers.Serializer):
    productName = serializers.CharField()
    displayName = serializers.SerializerMethodField()
    amount = serializers.IntegerField()
    image_url = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()

    def get_displayName(self, obj):
        request = self.context.get("request")
        lang = request.GET.get("lang", "en") if request else "en"

        return translate_text(obj.get("productName"), lang)

    def get_product(self, obj):
        product_name = obj.get("productName")

        try:
            return Product.objects.get(name=product_name)
        except Product.DoesNotExist:
            return None

    def get_image_url(self, obj):
        product = self.get_product(obj)
        return product.image_url.url if product and product.image_url else None

    def get_description(self, obj):
        product = self.get_product(obj)
        return product.description if product else None



class EventsCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = EventsCategory
        fields = ["id", "name"]


class EventSeedSerializer(serializers.ModelSerializer):
    category = EventsCategorySerializer(read_only=True)

    class Meta:
        model = Event
        fields = "__all__"


class EventSerializer(serializers.ModelSerializer):
    title = serializers.CharField()
    subtitle = serializers.CharField()
    category = EventsCategorySerializer(read_only=True)

    class Meta:
        model = Event
        fields = [
            "id",
            "title",
            "subtitle",
            "city",
            "start_date",
            "category",
            "end_date",
            "price",
            "image",
        ]
