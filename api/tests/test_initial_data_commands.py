from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from PIL import Image as PILImage

from api.models import Image, Mission, Plant, Product, Shop


def create_fake_image_files():
    image_paths = [
        "plants/dahlia_pinnata/dahlia_pinnata_seed.png",
        "plants/dahlia_pinnata/dahlia_pinnata_germination.png",
        "plants/dahlia_pinnata/dahlia_pinnata_growth.png",
        "plants/dahlia_pinnata/dahlia_pinnata_mature.png",
        "plants/dahlia_pinnata/dahlia_pinnata_flowering.png",
        "plants/dahlia_pinnata/dahlia_pinnata_dead.png",
        "plants/rosa_rugosa/rosa_rugosa_seed.png",
        "plants/rosa_rugosa/rosa_rugosa_germination.png",
        "plants/rosa_rugosa/rosa_rugosa_growth.png",
        "plants/rosa_rugosa/rosa_rugosa_mature.png",
        "plants/rosa_rugosa/rosa_rugosa_flowering.png",
        "plants/rosa_rugosa/rosa_rugosa_dead.png",
        "plants/orchidaceae/orchidaceae_seed.png",
        "plants/orchidaceae/orchidaceae_germination.png",
        "plants/orchidaceae/orchidaceae_growth.png",
        "plants/orchidaceae/orchidaceae_mature.png",
        "plants/orchidaceae/orchidaceae_flowering.png",
        "plants/orchidaceae/orchidaceae_dead.png",
        "plants/dendrobium_anosmum/dendrobium_anosmum_seed.png",
        "plants/dendrobium_anosmum/dendrobium_anosmum_germination.png",
        "plants/dendrobium_anosmum/dendrobium_anosmum_growth.png",
        "plants/dendrobium_anosmum/dendrobium_anosmum_mature.png",
        "plants/dendrobium_anosmum/dendrobium_anosmum_flowering.png",
        "plants/dendrobium_anosmum/dendrobium_anosmum_dead.png",
    ]

    for image_path in image_paths:
        full_path = Path(settings.MEDIA_ROOT) / image_path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        if not full_path.exists():
            PILImage.new("RGB", (1, 1)).save(full_path)


def test_sync_plants_creates_initial_plants(db):
    call_command("sync_plants")

    assert Plant.objects.count() == 4
    assert Plant.objects.filter(scientificName="dahlia_pinnata").exists()
    assert Plant.objects.filter(scientificName="rosa_rugosa").exists()
    assert Plant.objects.filter(scientificName="orchidaceae").exists()
    assert Plant.objects.filter(scientificName="dendrobium_anosmum").exists()


def test_sync_images_creates_initial_images(db):
    create_fake_image_files()

    call_command("sync_plants")
    call_command("sync_images")

    assert Image.objects.count() == 24
    assert Image.objects.filter(
        plant__scientificName="dahlia_pinnata",
        growthPhase="seed",
    ).exists()


def test_sync_products_creates_initial_products(db):
    call_command("sync_products")

    assert Product.objects.count() == 10

    assert Product.objects.filter(
        name="Small Heal",
        effectType="health",
    ).exists()

    assert Product.objects.filter(
        name="Phase Boost",
        effectType="growth",
    ).exists()

    # ARREGLAT:
    assert Product.objects.filter(
        name="Solar Shield",
        effectType="sun_protection",
    ).exists()

    assert Product.objects.filter(
        name="Protection Shield",
        effectType="meteo_protection",
    ).exists()

    assert Product.objects.filter(
        name="Wind Shield",
        effectType="wind_protection",
    ).exists()

    assert Product.objects.filter(
        name="Temperature Shield",
        effectType="temp_protection",
    ).exists()

    assert Product.objects.filter(
        name="Revive",
        effectType="revive",
    ).exists()


def test_sync_shop_initializes_starter_stock(db):
    call_command("sync_plants")
    call_command("sync_shop")

    shop = Shop.get_solo()

    assert shop.seeds["dahlia_pinnata"] > 0
    assert shop.seeds["rosa_rugosa"] > 0
    assert shop.seeds["orchidaceae"] > 0
    assert shop.seeds["dendrobium_anosmum"] > 0


def test_sync_missions_creates_initial_missions(db):
    call_command("sync_products")
    call_command("sync_missions")

    assert Mission.objects.count() == 11

    assert Mission.objects.filter(
        name="First Plant",
        action="PLANT",
    ).exists()

    assert Mission.objects.filter(
        name="Hard Lesson",
        action="DIE",
    ).exists()

    hard_lesson = Mission.objects.get(name="Hard Lesson")
    assert hard_lesson.productReward.name == "Revive"


def test_seed_initial_data_runs_all_commands(db):
    create_fake_image_files()

    call_command("seed_initial_data")

    assert Plant.objects.count() == 4
    assert Image.objects.count() == 24
    assert Product.objects.count() == 10
    assert Mission.objects.count() == 11

    shop = Shop.get_solo()
    assert shop.seeds["dahlia_pinnata"] > 0
