from django.contrib import admin

from .models import (AlbumEntry, Avatar, Garden, Image, Inventory, Mission,
                     Plant, PlantInGarden, Pot, Shop, Station, User,
                     UserMission, WeatherReading)

# Register your models here.


class InventoryInline(admin.StackedInline):
    model = Inventory
    extra = 0


class AvatarInline(admin.StackedInline):
    model = Avatar
    extra = 0


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        "username",
        "email",
        "city",
        "language",
        "stationCode",
        "is_staff",
        "is_active",
    )
    search_fields = ("username", "email", "city", "stationCode")
    list_filter = ("language", "is_staff", "is_active")
    ordering = ("username",)
    inlines = [AvatarInline, InventoryInline]
    readonly_fields = ("lastEntry",)


class ImageInline(admin.TabularInline):
    model = Image
    extra = 0


@admin.register(Plant)
class PlantAdmin(admin.ModelAdmin):
    list_display = (
        "scientificName",
        "commonName",
        "family",
        "canFlower",
        "minTemperature",
        "maxTemperature",
    )
    search_fields = ("scientificName", "commonName", "family")
    list_filter = ("canFlower",)
    ordering = ("scientificName",)
    # inlines = [ImageInline]


class PotInline(admin.TabularInline):
    model = Pot
    extra = 1


@admin.register(Garden)
class GardenAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "user", "availablePots")
    search_fields = ("name", "user__username")
    ordering = ("name",)
    inlines = [PotInline]


@admin.register(PlantInGarden)
class PlantInGardenAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "pot",
        "plant",
        "growthPhase",
        "healthLevel",
        "waterLevel",
        "plantedAt",
    )
    search_fields = (
        "plant__scientificName",
        "plant__commonName",
        "pot__garden__user__username",
    )
    list_filter = ("growthPhase",)
    ordering = ("-plantedAt",)
    readonly_fields = ("plantedAt", "lastWateredAt", "lastSimulatedAt")


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ("user", "coins")
    search_fields = ("user__username",)
    ordering = ("user",)


class PlantGardenInline(admin.TabularInline):
    model = PlantInGarden
    extra = 0


@admin.register(Pot)
class PotAdmin(admin.ModelAdmin):
    list_display = ("id", "garden", "number", "occupied")
    list_filter = ("occupied",)
    search_fields = ("garden__name", "garden__user__username")
    inlines = [PlantGardenInline]


@admin.register(Avatar)
class AvatarAdmin(admin.ModelAdmin):
    list_display = ("user", "expression", "hair_color", "clothing")
    search_fields = ("user__username",)


@admin.register(AlbumEntry)
class AlbumEntryAdmin(admin.ModelAdmin):
    list_display = ("user", "plant", "discoveryDate")
    search_fields = ("user__username", "plant__scientificName")


@admin.register(Mission)
class MissionAdmin(admin.ModelAdmin):
    list_display = ("name", "description", "rewardCoins", "product")


@admin.register(UserMission)
class UserMissionAdmin(admin.ModelAdmin):
    list_display = ("user", "mission", "missionState")
    list_filter = ("missionState",)


@admin.register(Station)
class StationAdmin(admin.ModelAdmin):
    list_display = ("stationCode", "station", "city", "temperature")
    readonly_fields = ("updateDate",)


@admin.register(WeatherReading)
class WeatherReadingAdmin(admin.ModelAdmin):
    list_display = ("station", "timestamp", "temperature", "precipitation")
    list_filter = ("station",)


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ("id",)
