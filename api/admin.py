# from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import User, Plant, UserMission, Mission, Shop


admin.site.register(User)
admin.site.register(Plant)
admin.site.register(UserMission)
admin.site.register(Mission)
admin.site.register(Shop)