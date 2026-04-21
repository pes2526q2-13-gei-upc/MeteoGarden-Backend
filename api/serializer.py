from rest_framework import serializers

from api.models import Image, Plant, Pot


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

        image = Image.objects.filter(plant=planting.plant).first()
        image_url = image.url.url if image and image.url else None

        return {
            "scientific_name": planting.plant.scientificName,
            "common_name": planting.plant.commonName,
            "family": planting.plant.family,
            "can_flower": planting.plant.canFlower,
            "min_temperature": planting.plant.minTemperature,
            "max_temperature": planting.plant.maxTemperature,
            "image_url": image_url,
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

    def get_image_url(self, obj):
        scientific_name = obj.get("scientificName")

        try:
            plant = Plant.objects.get(scientificName=scientific_name)
        except Plant.DoesNotExist:
            return None

        image = Image.objects.filter(plant=plant, growthPhase="mature").first()

        return image.url.url if image and image.url else None


class ShopSeedSerializer(serializers.Serializer):
    scientificName = serializers.CharField()
    commonName = serializers.CharField()
    family = serializers.CharField()
    description = serializers.CharField()
    price = serializers.IntegerField()
    image_url = serializers.SerializerMethodField()

    def get_image_url(self, obj):
        scientific_name = obj.get("scientificName")
        try:
            plant = Plant.objects.get(scientificName=scientific_name)
        except Plant.DoesNotExist:
            return None
        image = Image.objects.filter(plant=plant, growthPhase="seed").first()
        return image.url.url if image and image.url else None
