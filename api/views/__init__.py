from .views import health  # noqa: F401
from .views_collect import collect_plant  # noqa: F401
from .views_identify import identifyPlant  # noqa: F401
from .views_image import getUserAlbum  # noqa: F401
from .views_info import importPlant  # noqa: F401
from .views_plantar_planta import plant_seed  # noqa: F401
from .views_profile_operations import (  # noqa: F401
    edit_profile,
    get_profile,
    login,
    register,
)
from .views_visualitzarJardi import (  # noqa: F401
    garden_plants,
    plant_status,
    user_gardens,
    user_products,
    user_seeds,
    water_plant,
)
from .views_xema import current_weather, get_stations  # noqa: F401
