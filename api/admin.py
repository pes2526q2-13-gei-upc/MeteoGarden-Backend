# from django.contrib import admin

# Register your models here.
from django.contrib import admin

from .models import Mission, Plant, Shop, User, UserMission

admin.site.register(User)
admin.site.register(Plant)
admin.site.register(UserMission)
admin.site.register(Mission)
admin.site.register(Shop)
