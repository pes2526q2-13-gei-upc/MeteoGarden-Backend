from django.contrib import admin
from .models import (Plant, User, Avatar, Inventory, Garden, Pot, PlantInGarden,
                     FriendRequest, AlbumEntry, Image, Mission, UserMission, Station,
                     WeatherReading, Shop)

# Register your models here.
admin.site.register(User)
admin.site.register(Plant)
admin.site.register(Garden)
admin.site.register(PlantInGarden)
admin.site.register(Inventory)