from .views import health  # noqa: F401
from .views_avatar import avatar, getUserAvatar, saveAvatar  # noqa: F401
from .views_collect import collect_plant  # noqa: F401
from .views_identify import identifyPlant  # noqa: F401
from .views_image import getUserAlbum  # noqa: F401
from .views_info import importPlant  # noqa: F401
from .views_missions import createMission  # noqa: F401
from .views_missions import assignMission, getMissions, getUserMissions
from .views_plantar_planta import delete_plant, plant_seed  # noqa: F401
from .views_products import use_product  # noqa: F401
from .views_profile_operations import delete_profile  # noqa: F401
from .views_profile_operations import (
    edit_profile,
    get_profile,
    google_register,
    google_verify,
    login,
    register,
    validate_token,
)
from .views_shop import buy_item, get_shop  # noqa: F401
from .views_translate import translate  # noqa: F401
from .views_visualitzarJardi import plant_status  # noqa: F401
from .views_visualitzarJardi import (
    garden_plants,
    user_gardens,
    user_products,
    user_seeds,
    water_plant,
)
from .views_xema import current_weather, get_stations  # noqa: F401
