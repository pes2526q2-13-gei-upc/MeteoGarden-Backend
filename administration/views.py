from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from api.models import (
    Mission,
    MissionAction,
    MissionState,
    Plant,
    PlantInGarden,
    Product,
    User,
    UserMission,
)


def _require_staff(request):
    if not request.user.is_authenticated or not request.user.is_staff:
        return redirect("adm_signin")
    return None


@require_GET
def signin(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect("adm_dashboard")
    return render(request, "administration/signin.html", {"errors": []})


@require_POST
def signin_submit(request):
    username = request.POST.get("username", "").strip()
    password = request.POST.get("password", "")
    user = authenticate(request, username=username, password=password)

    if user is not None and user.is_staff and user.is_active:
        login(request, user)
        return redirect("adm_dashboard")

    return render(
        request,
        "administration/signin.html",
        {"errors": ["Credencials incorrectes o sense permisos d'administrador."]},
    )


@require_POST
def signout(request):
    logout(request)
    return redirect("adm_signin")


@require_GET
def dashboard(request):
    guard = _require_staff(request)
    if guard:
        return guard

    context = {
        "num_users": User.objects.count(),
        "num_plants_active": PlantInGarden.objects.exclude(growthPhase="dead").count(),
        "num_missions": Mission.objects.count(),
        "num_products": Product.objects.count(),
        "missions": Mission.objects.all().order_by("name")[:8],
        "recent_users": User.objects.order_by("-lastEntry")[:5],
    }
    return render(request, "administration/dashboard.html", context)


@require_GET
def missions(request):
    guard = _require_staff(request)
    if guard:
        return guard

    return render(
        request,
        "administration/missions.html",
        {"missions": Mission.objects.all().order_by("name")},
    )


def _mission_form_context():
    return {
        "plants": Plant.objects.all().order_by("scientificName"),
        "products": Product.objects.all().order_by("name"),
        "actions": MissionAction.choices,
    }


@require_GET
def mission_create(request):
    guard = _require_staff(request)
    if guard:
        return guard

    ctx = _mission_form_context()
    ctx["action_label"] = "Crear missió"
    return render(request, "administration/mission_form.html", ctx)


@require_POST
def mission_create_submit(request):
    guard = _require_staff(request)
    if guard:
        return guard

    try:
        mission = Mission(
            name=request.POST["name"].strip(),
            description=request.POST["description"].strip(),
            action=request.POST["action"],
            goal=int(request.POST.get("goal", 1)),
            rewardCoins=int(request.POST.get("rewardCoins", 0)),
        )

        plant_pk = request.POST.get("plant")
        if plant_pk:
            mission.plant = Plant.objects.get(pk=plant_pk)

        product_pk = request.POST.get("product")
        if product_pk:
            mission.product = Product.objects.get(pk=product_pk)

        plant_reward_pk = request.POST.get("plantReward")
        if plant_reward_pk:
            mission.plantReward = Plant.objects.get(pk=plant_reward_pk)

        product_reward_pk = request.POST.get("productReward")
        if product_reward_pk:
            mission.productReward = Product.objects.get(pk=product_reward_pk)

        mission.save()
        messages.success(request, f"Missió «{mission.name}» creada correctament.")
        return redirect("adm_missions")
    except Exception as e:
        messages.error(request, f"Error: {e}")
        return redirect("adm_mission_create")


@require_GET
def mission_edit(request, name):
    guard = _require_staff(request)
    if guard:
        return guard

    ctx = _mission_form_context()
    ctx["mission"] = get_object_or_404(Mission, pk=name)
    ctx["action_label"] = "Guardar canvis"
    return render(request, "administration/mission_form.html", ctx)


@require_POST
def mission_edit_submit(request, name):
    guard = _require_staff(request)
    if guard:
        return guard

    mission = get_object_or_404(Mission, pk=name)

    try:
        mission.description = request.POST["description"].strip()
        mission.action = request.POST["action"]
        mission.goal = int(request.POST.get("goal", 1))
        mission.rewardCoins = int(request.POST.get("rewardCoins", 0))

        plant_pk = request.POST.get("plant")
        mission.plant = Plant.objects.get(pk=plant_pk) if plant_pk else None

        product_pk = request.POST.get("product")
        mission.product = Product.objects.get(pk=product_pk) if product_pk else None

        plant_reward_pk = request.POST.get("plantReward")
        mission.plantReward = (
            Plant.objects.get(pk=plant_reward_pk) if plant_reward_pk else None
        )

        product_reward_pk = request.POST.get("productReward")
        mission.productReward = (
            Product.objects.get(pk=product_reward_pk) if product_reward_pk else None
        )

        mission.save()
        messages.success(request, f"Missió «{mission.name}» actualitzada.")
        return redirect("adm_missions")
    except Exception as e:
        messages.error(request, f"Error: {e}")
        return redirect("adm_mission_edit", name=name)


@require_POST
def mission_delete(request, name):
    guard = _require_staff(request)
    if guard:
        return guard

    mission = get_object_or_404(Mission, pk=name)
    mission.delete()
    messages.success(request, f"Missió «{name}» eliminada.")
    return redirect("adm_missions")


@require_POST
def mission_assign_all(request, name):
    guard = _require_staff(request)
    if guard:
        return guard

    mission = get_object_or_404(Mission, pk=name)
    created = 0

    for user in User.objects.all():
        _, was_created = UserMission.objects.get_or_create(
            user=user,
            mission=mission,
            defaults={
                "missionState": MissionState.IN_PROGRESS,
                "current": 0,
                "acquiredAt": timezone.now(),
            },
        )
        if was_created:
            created += 1

    messages.success(request, f"Missió assignada a {created} usuaris nous.")
    return redirect("adm_missions")


@require_GET
def products(request):
    guard = _require_staff(request)
    if guard:
        return guard

    return render(
        request,
        "administration/products.html",
        {"products": Product.objects.all().order_by("name")},
    )


@require_GET
def product_create(request):
    guard = _require_staff(request)
    if guard:
        return guard

    return render(
        request,
        "administration/product_form.html",
        {
            "effect_types": Product.EFFECT_TYPES,
            "action_label": "Crear producte",
        },
    )


@require_POST
def product_create_submit(request):
    guard = _require_staff(request)
    if guard:
        return guard

    try:
        product = Product(
            name=request.POST["name"].strip(),
            description=request.POST["description"].strip(),
            effectType=request.POST["effectType"],
            price=int(request.POST.get("price", 0)),
            isInstant=request.POST.get("isInstant") == "on",
            rarity=request.POST.get("rarity", "common").strip(),
        )

        value = request.POST.get("value")
        if value:
            product.value = float(value)

        duration = request.POST.get("durationHours")
        if duration:
            product.durationHours = float(duration)

        if "image_url" in request.FILES:
            product.image_url = request.FILES["image_url"]

        product.save()
        messages.success(request, f"Producte «{product.name}» creat correctament.")
        return redirect("adm_products")
    except Exception as e:
        messages.error(request, f"Error: {e}")
        return redirect("adm_product_create")


@require_GET
def product_edit(request, name):
    guard = _require_staff(request)
    if guard:
        return guard

    return render(
        request,
        "administration/product_form.html",
        {
            "product": get_object_or_404(Product, pk=name),
            "effect_types": Product.EFFECT_TYPES,
            "action_label": "Guardar canvis",
        },
    )


@require_POST
def product_edit_submit(request, name):
    guard = _require_staff(request)
    if guard:
        return guard

    product = get_object_or_404(Product, pk=name)

    try:
        product.description = request.POST["description"].strip()
        product.effectType = request.POST["effectType"]
        product.price = int(request.POST.get("price", 0))
        product.isInstant = request.POST.get("isInstant") == "on"
        product.rarity = request.POST.get("rarity", "common").strip()

        value = request.POST.get("value")
        product.value = float(value) if value else None

        duration = request.POST.get("durationHours")
        product.durationHours = float(duration) if duration else None

        if "image_url" in request.FILES:
            product.image_url = request.FILES["image_url"]

        product.save()
        messages.success(request, f"Producte «{product.name}» actualitzat.")
        return redirect("adm_products")
    except Exception as e:
        messages.error(request, f"Error: {e}")
        return redirect("adm_product_edit", name=name)


@require_POST
def product_delete(request, name):
    guard = _require_staff(request)
    if guard:
        return guard

    product = get_object_or_404(Product, pk=name)
    product.delete()
    messages.success(request, f"Producte «{name}» eliminat.")
    return redirect("adm_products")


@require_GET
def users(request):
    guard = _require_staff(request)
    if guard:
        return guard

    return render(
        request,
        "administration/users.html",
        {"users": User.objects.order_by("username")},
    )
