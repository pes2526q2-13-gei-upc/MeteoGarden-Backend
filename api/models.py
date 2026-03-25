from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


# Enumerations
class GrowthState(models.TextChoices):
    SEED = "seed", "Seed"
    GERMINATION = "germination", "Germination"
    GROWTH = "growth", "Growth"
    MATURE = "mature", "Mature"
    FLOWERING = "flowering", "Flowering"
    DEAD = "dead", "Dead"


class AvatarExpression(models.TextChoices):
    HAPPY = "happy", "Happy"
    SAD = "sad", "Sad"
    SWEATING = "sweating", "Sweating"
    SHIVERING = "shivering", "Shivering"
    WET = "wet", "Wet"


class MissionState(models.TextChoices):
    COMPLETED = "completed", "Completed"
    CLAIMED = "claimed", "Claimed"
    IN_PROGRESS = "in progress", "In Progress"


class LanguageType(models.TextChoices):
    CATALAN = "catalan", "Catalan"
    SPANISH = "spanish", "Spanish"
    ENGLISH = "english", "English"


# Main classes
class Plant(models.Model):
    scientificName = models.CharField(max_length=100, primary_key=True)  # RT.1
    commonName = models.CharField(max_length=100)
    family = models.CharField(max_length=100, null=True)
    canFlower = models.BooleanField(default=False)
    minTemperature = models.FloatField(validators=[MinValueValidator(0.0)])  # RT.6
    maxTemperature = models.FloatField()  # RT.6
    description = models.TextField(blank=True, null=True)

    def clean(self):
        if self.minTemperature >= self.maxTemperature:
            raise ValidationError(
                "The minimum temperature must be lower "
                "than the "
                "maximum temperature."
            )

    def __str__(self):
        return self.scientificName


class User(AbstractUser):
    username = models.CharField(primary_key=True)  # RT.1
    email = models.EmailField(unique=True)  # RT.14
    city = models.CharField(max_length=50)
    language = models.CharField(
        max_length=50, choices=LanguageType.choices, default=LanguageType.CATALAN
    )
    lastEntry = models.DateTimeField(auto_now=True)
    numPlantsCollected = models.PositiveIntegerField(default=0)
    stationCode = models.CharField(max_length=4)

    @property
    def numPlantsUnlocked(self):
        return self.albumentry_set.count()

    def __str__(self):
        return self.username


class Avatar(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, primary_key=True
    )  # RT.1
    body = models.CharField(max_length=50)
    skinTone = models.CharField(max_length=50)
    eyeColor = models.CharField(max_length=50)
    expression = models.CharField(max_length=50, choices=AvatarExpression.choices)
    hairColor = models.CharField(max_length=50)
    hairStyle = models.CharField(max_length=50)
    facialHair = models.CharField(max_length=50, blank=True)
    accessories = models.JSONField(default=list, blank=True)
    clothing = models.CharField(max_length=50)

    def addAccessory(self, accessory):
        if accessory not in self.accessories:
            self.accessories.append(accessory)
            self.save()

    def removeAccessory(self, accessory):
        if accessory in self.accessories:
            self.accessories.remove(accessory)
            self.save()

    def __str__(self):
        return self.user.username


class Inventory(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, primary_key=True
    )  # RT.1
    # All users start with 5 coins
    coins = models.PositiveIntegerField(default=5)
    seeds = models.JSONField(default=dict, blank=True)
    products = models.JSONField(default=dict, blank=True)

    def clean(self):
        from .models import AlbumEntry

        for seed in self.seeds:
            if seed not in AlbumEntry.objects.filter(user=self.user).values_list(
                "plant__scientificName", flat=True
            ):
                raise (ValidationError(f"Seed '{seed}' is not in the user's album."))

    def addSeed(self, scientificName, quantity):
        if quantity < 0:  # RT.6
            raise ValueError("Quantity cannot be negative")
        if not AlbumEntry.objects.filter(
            user=self.user, plant__scientificName=scientificName
        ).exists():  # RT.13
            raise ValueError(f"Plant '{scientificName}' is not in the user's album.")
        self.seeds[scientificName] = self.seeds.get(scientificName, 0) + quantity
        self.save()

    def addProduct(self, productName, quantity):
        if quantity < 0:  # RT.6
            raise ValueError("Quantity cannot be negative")

        self.products[productName] = self.products.get(productName, 0) + quantity
        self.save()

    def removeSeed(self, scientificName, quantity):
        current = self.seeds.get(scientificName, 0)
        if quantity > current:
            raise ValueError(
                f"Cannot remove {quantity} seeds of"
                f" '{scientificName}': only {current} available."
            )
        self.seeds[scientificName] = current - quantity
        if self.seeds[scientificName] == 0:
            del self.seeds[scientificName]
        self.save()

    def removeProduct(self, productName, quantity):
        current = self.products.get(productName, 0)
        if quantity > current:
            raise ValueError(
                f"Cannot remove {quantity} products of "
                f"'{productName}': only {current} availeble."
            )
        self.products[productName] = current - quantity
        if self.products[productName] == 0:
            del self.products[productName]
        self.save()

    def __str__(self):
        return self.user.username


class Garden(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # RT.1
    name = models.CharField(max_length=100)

    class Meta:
        unique_together = ("user", "name")

    @property
    def availablePots(self):
        totalPots = self.pot_set.count()
        occupied = self.pot_set.filter(occupied=True).count()
        return totalPots - occupied

    def rename(self, new_name):
        if Garden.objects.filter(user=self.user, name=new_name).exists():
            raise ValidationError("You already have a garden with this name.")
        self.name = new_name
        self.save()

    def __str__(self):
        return f"Garden {self.name} of {self.user.username}"


class Pot(models.Model):
    garden = models.ForeignKey(Garden, on_delete=models.CASCADE)
    number = models.PositiveIntegerField()
    occupied = models.BooleanField(default=False)

    class Meta:
        unique_together = ("garden", "number")

    def __str__(self):
        return f"Pot {self.number} ({self.garden.name})"


class PlantInGarden(models.Model):
    pot = models.OneToOneField(Pot, on_delete=models.CASCADE)
    plant = models.ForeignKey(Plant, on_delete=models.CASCADE)
    plantedAt = models.DateTimeField(default=timezone.now)
    growthPhase = models.CharField(
        max_length=50, choices=GrowthState.choices, default=GrowthState.SEED
    )
    healthLevel = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)]
    )  # RT.11
    waterLevel = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)]
    )  # RT.11
    lastWateredAt = models.DateTimeField(default=timezone.now)
    lastSimulatedAt = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("pot", "plant", "plantedAt")

    def clean(self):
        if (
            self.growthPhase == GrowthState.FLOWERING and not self.plant.canFlower
        ):  # RT.2: No flowering if canFlower is false
            raise ValidationError("This plant cannot flower.")
        if (
            self.lastWateredAt < self.plantedAt
        ):  # RT.10: Last watered time after planting time
            raise ValidationError(
                "The last watered date/time must be after " "the planting " "date/time."
            )

    def save(self, *args, **kwargs):
        # RT.3: If a PlantInGarden is created, the pot becomes occupied
        self.pot.occupied = True
        self.pot.save()
        super().save(*args, **kwargs)

    def update(self, health=None, water=None, phase=None):
        if health is not None:
            self.healthLevel = health
        if water is not None:
            self.waterLevel = water
            self.lastWateredAt = timezone.now()
        if phase is not None:
            self.growthPhase = phase
        self.save()

    def delete(self, *args, **kwargs):
        # RT.3: If a PlantInGarden is deleted, the pot becomes unoccupied
        self.pot.occupied = False
        self.pot.save()
        super().delete(*args, **kwargs)


class FriendRequest(models.Model):
    requester = models.ForeignKey(
        User, related_name="sent_requests", on_delete=models.CASCADE
    )
    requested = models.ForeignKey(
        User, related_name="received_requests", on_delete=models.CASCADE
    )
    accepted = models.BooleanField(null=True, blank=True)

    class Meta:
        unique_together = ("requester", "requested")

    def clean(self):
        if self.requester == self.requested:  # RT.4: No request to oneself
            raise ValidationError("You cannot send a friend request to yourself.")

    def accept(self):
        self.accepted = True
        self.save()

    def reject(self):
        self.accepted = False
        self.save()


class AlbumEntry(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    plant = models.ForeignKey(Plant, on_delete=models.CASCADE)
    discoveryDate = models.DateField(default=timezone.now)
    description = models.TextField()

    class Meta:
        unique_together = ("user", "plant")

    def clean(self):
        if self.discoveryDate > self.user.lastEntry.date():
            raise ValidationError(
                "The discovery date cannot be after " "the user's last entry date."
            )


def imageUploadPath(instance, filename):
    sci = instance.plant.scientificName.replace(" ", "_").lower()
    return f"plants/{sci}/{filename}"


class Image(models.Model):
    plant = models.ForeignKey(Plant, on_delete=models.CASCADE, null=True, blank=True)
    uploader = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    url = models.ImageField(
        upload_to=imageUploadPath,
        width_field="width",
        height_field="height",
    )
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return f"Image of {self.plant.scientificName} by " f"{self.uploader.username}"


class Mission(models.Model):
    name = models.CharField(max_length=50, primary_key=True)  # RT.1
    description = models.TextField()
    seed = models.ForeignKey(Plant, on_delete=models.CASCADE)
    rewardCoins = models.PositiveIntegerField()
    product = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class UserMission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    mission = models.ForeignKey(Mission, on_delete=models.CASCADE)
    missionState = models.CharField(max_length=50, choices=MissionState.choices)
    acquiredAt = models.DateTimeField()

    class Meta:
        unique_together = ("user", "mission")


class Station(models.Model):
    stationCode = models.CharField(max_length=4, primary_key=True)  # RT.1
    station = models.CharField(max_length=50)
    city = models.CharField(max_length=50)
    solarIrradiance = models.PositiveBigIntegerField()
    temperature = models.FloatField()
    windSpeed = models.FloatField(validators=[MinValueValidator(0.0)])
    relativeHumidity = models.FloatField(validators=[MinValueValidator(0.0)])
    precipitation = models.FloatField(validators=[MinValueValidator(0.0)])
    updateDate = models.DateTimeField(auto_now=True)


class WeatherReading(models.Model):
    station = models.ForeignKey(
        Station,
        on_delete=models.CASCADE,
        related_name="weather_readings",
    )
    timestamp = models.DateTimeField()
    temperature = models.FloatField(null=True, blank=True)  # ºC       (var 32)
    precipitation = models.FloatField(null=True, blank=True)  # mm       (var 35)
    solarIrradiance = models.FloatField(null=True, blank=True)  # W/m²     (var 36)
    windSpeed = models.FloatField(null=True, blank=True)  # m/s      (var 30)
    relativeHumidity = models.FloatField(null=True, blank=True)  # %        (var 33)

    class Meta:
        unique_together = ("station", "timestamp")
        indexes = [
            models.Index(fields=["station", "timestamp"]),
        ]
        ordering = ["timestamp"]

    def __str__(self):
        return f"{self.station.stationCode} @ {self.timestamp}"


class Shop(models.Model):
    seeds = models.JSONField(default=dict, blank=True)
    products = models.JSONField(default=dict, blank=True)

    def update_stock(self, item_type, name, price):
        if item_type == "seed":
            self.seeds[name] = price
        elif item_type == "product":
            self.products[name] = price
        self.save()

    def remove_item(self, item_type, name):
        if item_type == "seed" and name in self.seeds:
            del self.seeds[name]
        elif item_type == "product" and name in self.products:
            del self.products[name]
        self.save()

    def save(self, *args, **kwargs):
        if not self.pk and Shop.objects.exists():
            raise Exception("Shop already exists.")
        return super().save(*args, **kwargs)
