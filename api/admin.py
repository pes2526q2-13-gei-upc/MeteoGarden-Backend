from django.contrib import admin
from django.utils.html import format_html

from .models import (
    ActiveProduct,
    AlbumEntry,
    Avatar,
    Device,
    Event,
    EventsCategory,
    FriendRequest,
    Garden,
    Image,
    Inventory,
    Mission,
    Plant,
    PlantInGarden,
    Pot,
    Product,
    Shop,
    Station,
    User,
    UserMission,
    WeatherReading,
)

# ──────────────────────────────────────────────
# Site branding
# ──────────────────────────────────────────────
admin.site.site_header = "🌿 MeteoGarden Admin"
admin.site.site_title = "MeteoGarden"
admin.site.index_title = "Panell d'administració"


# ──────────────────────────────────────────────
# Inlines
# ──────────────────────────────────────────────
class AvatarInline(admin.StackedInline):
    model = Avatar
    extra = 0
    can_delete = False


class InventoryInline(admin.StackedInline):
    model = Inventory
    extra = 0
    can_delete = False
    readonly_fields = ("coins", "seeds", "products")


class DeviceInline(admin.TabularInline):
    model = Device
    extra = 0
    readonly_fields = ("short_token", "createdAt")
    fields = ("short_token", "createdAt")

    def short_token(self, obj):
        return f"{obj.token[:12]}…" if obj.token else "—"

    short_token.short_description = "Token (truncat)"


class ImageInline(admin.TabularInline):
    model = Image
    extra = 0
    readonly_fields = ("image_preview",)
    fields = ("image_preview", "growthPhase", "uploader")

    def image_preview(self, obj):
        if obj.url:
            return format_html('<img src="{}" style="max-height:60px;"/>', obj.url.url)
        return "—"

    image_preview.short_description = "Previsualització"


class PotInline(admin.TabularInline):
    model = Pot
    extra = 0
    readonly_fields = ("occupied",)


class PlantInGardenInline(admin.TabularInline):
    model = PlantInGarden
    extra = 0
    readonly_fields = ("plantedAt", "lastWateredAt", "lastSimulatedAt")
    fields = ("plant", "growthPhase", "healthLevel", "waterLevel", "plantedAt")


class ActiveProductInline(admin.TabularInline):
    model = ActiveProduct
    extra = 0
    readonly_fields = ("applied_at", "is_active_display")
    fields = ("product", "applied_at", "is_active_display")

    def is_active_display(self, obj):
        active = obj.is_active()
        color = "green" if active else "red"
        text = "Actiu" if active else "Caducat"
        return format_html('<span style="color:{}">&#9679; {}</span>', color, text)

    is_active_display.short_description = "Estat"


# ──────────────────────────────────────────────
# User
# ──────────────────────────────────────────────
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        "username",
        "email",
        "city",
        "language",
        "stationCode",
        "numPlantsCollected",
        "lastEntry",
        "is_staff",
        "is_active",
    )
    search_fields = ("username", "email", "city", "stationCode")
    list_filter = ("language", "is_staff", "is_active")
    ordering = ("username",)
    readonly_fields = ("lastEntry", "numPlantsCollected")
    inlines = [AvatarInline, InventoryInline, DeviceInline]

    fieldsets = (
        ("Identitat", {"fields": ("username", "email", "password")}),
        ("Perfil", {"fields": ("city", "language", "stationCode")}),
        (
            "Estadístiques",
            {"fields": ("numPlantsCollected", "lastEntry", "lastNotificationAt")},
        ),
        (
            "Permisos",
            {
                "fields": ("is_active", "is_staff", "is_superuser", "groups"),
                "classes": ("collapse",),
            },
        ),
    )


# ──────────────────────────────────────────────
# Plant
# ──────────────────────────────────────────────
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
    list_filter = ("canFlower", "family")
    ordering = ("scientificName",)
    inlines = [ImageInline]


# ──────────────────────────────────────────────
# Garden & Pot
# ──────────────────────────────────────────────
@admin.register(Garden)
class GardenAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "user", "availablePots", "likes")
    search_fields = ("name", "user__username")
    list_filter = ("user",)
    ordering = ("name",)
    list_select_related = ("user",)
    inlines = [PotInline]


@admin.register(Pot)
class PotAdmin(admin.ModelAdmin):
    list_display = ("id", "garden", "number", "occupied")
    list_filter = ("occupied",)
    search_fields = ("garden__name", "garden__user__username")
    list_select_related = ("garden__user",)
    inlines = [PlantInGardenInline]


# ──────────────────────────────────────────────
# PlantInGarden
# ──────────────────────────────────────────────
@admin.register(PlantInGarden)
class PlantInGardenAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "plant",
        "garden_name",
        "owner",
        "growthPhase",
        "health_bar",
        "water_bar",
        "plantedAt",
    )
    search_fields = (
        "plant__scientificName",
        "plant__commonName",
        "pot__garden__user__username",
        "pot__garden__name",
    )
    list_filter = ("growthPhase",)
    ordering = ("-plantedAt",)
    readonly_fields = ("plantedAt", "lastWateredAt", "lastSimulatedAt")
    list_select_related = ("plant", "pot__garden__user")
    inlines = [ActiveProductInline]

    def garden_name(self, obj):
        return obj.pot.garden.name

    garden_name.short_description = "Jardí"
    garden_name.admin_order_field = "pot__garden__name"

    def owner(self, obj):
        return obj.pot.garden.user.username

    owner.short_description = "Usuari"
    owner.admin_order_field = "pot__garden__user__username"

    def health_bar(self, obj):
        pct = int(obj.healthLevel)
        color = "green" if pct > 60 else ("orange" if pct > 30 else "red")
        return format_html(
            '<div style="width:80px;background:#eee;border-radius:4px;">'
            '<div style="width:{pct}%;background:{color};height:12px;border-radius:4px;"></div>'
            "</div> {pct}%",
            pct=pct,
            color=color,
        )

    health_bar.short_description = "Salut"

    def water_bar(self, obj):
        pct = int(obj.waterLevel)
        color = "#2196F3" if pct > 40 else "orange"
        return format_html(
            '<div style="width:80px;background:#eee;border-radius:4px;">'
            '<div style="width:{pct}%;background:{color};height:12px;border-radius:4px;"></div>'
            "</div> {pct}%",
            pct=pct,
            color=color,
        )

    water_bar.short_description = "Aigua"


# ──────────────────────────────────────────────
# Inventory
# ──────────────────────────────────────────────
@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ("user", "coins", "num_seeds", "num_products")
    search_fields = ("user__username",)
    ordering = ("-coins",)
    list_select_related = ("user",)

    def num_seeds(self, obj):
        return sum(obj.seeds.values()) if obj.seeds else 0

    num_seeds.short_description = "Total llavors"

    def num_products(self, obj):
        return sum(obj.products.values()) if obj.products else 0

    num_products.short_description = "Total productes"


# ──────────────────────────────────────────────
# Avatar
# ──────────────────────────────────────────────
@admin.register(Avatar)
class AvatarAdmin(admin.ModelAdmin):
    list_display = ("user", "expression", "hair_color", "clothing", "body")
    search_fields = ("user__username",)
    list_select_related = ("user",)


# ──────────────────────────────────────────────
# AlbumEntry
# ──────────────────────────────────────────────
@admin.register(AlbumEntry)
class AlbumEntryAdmin(admin.ModelAdmin):
    list_display = ("user", "plant", "discoveryDate")
    search_fields = ("user__username", "plant__scientificName", "plant__commonName")
    list_filter = ("discoveryDate",)
    date_hierarchy = "discoveryDate"
    list_select_related = ("user", "plant")


# ──────────────────────────────────────────────
# Product & ActiveProduct
# ──────────────────────────────────────────────
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "effectType",
        "rarity",
        "price",
        "isInstant",
        "durationHours",
        "product_image",
    )
    search_fields = ("name", "description")
    list_filter = ("effectType", "rarity", "isInstant")
    ordering = ("name",)

    def product_image(self, obj):
        if obj.image_url:
            return format_html(
                '<img src="{}" style="max-height:40px;"/>',
                obj.image_url.url,
            )
        return "—"

    product_image.short_description = "Imatge"


@admin.register(ActiveProduct)
class ActiveProductAdmin(admin.ModelAdmin):
    list_display = ("plant", "product", "applied_at", "is_active_display")
    list_filter = ("product",)
    readonly_fields = ("applied_at",)
    list_select_related = ("plant__pot__garden__user", "product")

    def is_active_display(self, obj):
        active = obj.is_active()
        color = "green" if active else "red"
        text = "Actiu" if active else "Caducat"
        return format_html('<span style="color:{}">&#9679; {}</span>', color, text)

    is_active_display.short_description = "Estat"


# ──────────────────────────────────────────────
# Shop
# ──────────────────────────────────────────────
@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ("id", "num_seeds", "num_products")

    def num_seeds(self, obj):
        return len(obj.seeds)

    num_seeds.short_description = "Tipus de llavors"

    def num_products(self, obj):
        return len(obj.products)

    num_products.short_description = "Tipus de productes"


# ──────────────────────────────────────────────
# Mission & UserMission
# ──────────────────────────────────────────────
@admin.register(Mission)
class MissionAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "action",
        "goal",
        "rewardCoins",
        "plant",
        "product",
        "plantReward",
        "productReward",
    )
    search_fields = ("name", "description")
    list_filter = ("action",)
    ordering = ("name",)


@admin.register(UserMission)
class UserMissionAdmin(admin.ModelAdmin):
    list_display = ("user", "mission", "missionState", "current", "acquiredAt")
    list_filter = ("missionState",)
    search_fields = ("user__username", "mission__name")
    ordering = ("-acquiredAt",)
    list_select_related = ("user", "mission")
    date_hierarchy = "acquiredAt"


# ──────────────────────────────────────────────
# Station & WeatherReading
# ──────────────────────────────────────────────
@admin.register(Station)
class StationAdmin(admin.ModelAdmin):
    list_display = (
        "stationCode",
        "station",
        "city",
        "temperature",
        "relativeHumidity",
        "precipitation",
        "windSpeed",
        "updateDate",
    )
    search_fields = ("stationCode", "station", "city")
    ordering = ("city",)
    readonly_fields = ("updateDate",)


@admin.register(WeatherReading)
class WeatherReadingAdmin(admin.ModelAdmin):
    list_display = (
        "station",
        "timestamp",
        "temperature",
        "precipitation",
        "relativeHumidity",
        "windSpeed",
        "solarIrradiance",
    )
    list_filter = ("station",)
    search_fields = ("station__stationCode", "station__city")
    ordering = ("-timestamp",)
    date_hierarchy = "timestamp"
    list_select_related = ("station",)


# ──────────────────────────────────────────────
# FriendRequest
# ──────────────────────────────────────────────
@admin.register(FriendRequest)
class FriendRequestAdmin(admin.ModelAdmin):
    list_display = (
        "requester",
        "requested",
        "accepted",
        "likeToRequester",
        "likeToRequested",
    )
    list_filter = ("accepted",)
    search_fields = ("requester__username", "requested__username")
    list_select_related = ("requester", "requested")


# ──────────────────────────────────────────────
# Device
# ──────────────────────────────────────────────
@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ("user", "short_token", "createdAt")
    search_fields = ("user__username",)
    readonly_fields = ("token", "createdAt")
    ordering = ("-createdAt",)
    list_select_related = ("user",)

    def short_token(self, obj):
        return f"{obj.token[:16]}…" if obj.token else "—"

    short_token.short_description = "Token (truncat)"


# ──────────────────────────────────────────────
# Events
# ──────────────────────────────────────────────
@admin.register(EventsCategory)
class EventsCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "num_events")
    search_fields = ("name",)

    def num_events(self, obj):
        return obj.events.count()

    num_events.short_description = "Nombre d'esdeveniments"


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "category",
        "city",
        "start_date",
        "end_date",
        "price",
        "event_image",
    )
    search_fields = ("title", "subtitle", "city", "street")
    list_filter = ("category", "city")
    ordering = ("start_date",)
    date_hierarchy = "start_date"
    list_select_related = ("category",)

    def event_image(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height:40px;"/>',
                obj.image.url,
            )
        return "—"

    event_image.short_description = "Imatge"
