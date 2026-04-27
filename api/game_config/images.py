from api.models import GrowthState

STARTER_IMAGES = [
    # --- citrus_sinensis ---
    {"plant": "citrus_sinensis", "phase": GrowthState.SEED,        "url": "plants/citrus_sinensis/citrus_sinensis_seed.png"},
    {"plant": "citrus_sinensis", "phase": GrowthState.GERMINATION, "url": "plants/citrus_sinensis/citrus_sinensis_germination.png"},
    {"plant": "citrus_sinensis", "phase": GrowthState.GROWTH,      "url": "plants/citrus_sinensis/citrus_sinensis_growth.png"},
    {"plant": "citrus_sinensis", "phase": GrowthState.MATURE,      "url": "plants/citrus_sinensis/citrus_sinensis_mature.png"},
    {"plant": "citrus_sinensis", "phase": GrowthState.FLOWERING,   "url": "plants/citrus_sinensis/citrus_sinensis_flowering.png"},
    {"plant": "citrus_sinensis", "phase": GrowthState.DEAD,        "url": "plants/citrus_sinensis/citrus_sinensis_dead.png"},

    # --- dianthus_caryophyllus ---
    {"plant": "dianthus_caryophyllus", "phase": GrowthState.SEED,        "url": "plants/dianthus_caryophyllus/dianthus_caryophyllus_seed.png"},
    {"plant": "dianthus_caryophyllus", "phase": GrowthState.GERMINATION, "url": "plants/dianthus_caryophyllus/dianthus_caryophyllus_germination.png"},
    {"plant": "dianthus_caryophyllus", "phase": GrowthState.GROWTH,      "url": "plants/dianthus_caryophyllus/dianthus_caryophyllus_growth.png"},
    {"plant": "dianthus_caryophyllus", "phase": GrowthState.MATURE,      "url": "plants/dianthus_caryophyllus/dianthus_caryophyllus_mature.png"},
    {"plant": "dianthus_caryophyllus", "phase": GrowthState.FLOWERING,   "url": "plants/dianthus_caryophyllus/dianthus_caryophyllus_flowering.png"},
    {"plant": "dianthus_caryophyllus", "phase": GrowthState.DEAD,        "url": "plants/dianthus_caryophyllus/dianthus_caryophyllus_dead.png"},

    # --- helianthus_annuus ---
    {"plant": "helianthus_annuus", "phase": GrowthState.SEED,        "url": "plants/helianthus_annuus/helianthus_annuus_seed_ugsoSEG.png"},
    {"plant": "helianthus_annuus", "phase": GrowthState.GERMINATION, "url": "plants/helianthus_annuus/helianthus_annuus_germination_HdfR45a.png"},
    {"plant": "helianthus_annuus", "phase": GrowthState.GROWTH,      "url": "plants/helianthus_annuus/helianthus_annuus_growth_MVx3vF1.png"},
    {"plant": "helianthus_annuus", "phase": GrowthState.MATURE,      "url": "plants/helianthus_annuus/helianthus_annuus_mature_VG25ckP.png"},
    {"plant": "helianthus_annuus", "phase": GrowthState.FLOWERING,   "url": "plants/helianthus_annuus/helianthus_annuus_flowering_raa4TSh.png"},
    {"plant": "helianthus_annuus", "phase": GrowthState.DEAD,        "url": "plants/helianthus_annuus/helianthus_annuus_dead_XXzT081.png"},

    # --- mentha_spicata ---
    {"plant": "mentha_spicata", "phase": GrowthState.SEED,        "url": "plants/mentha_spicata/mentha_spicata_seed_MtlVPcW.png"},
    {"plant": "mentha_spicata", "phase": GrowthState.GERMINATION, "url": "plants/mentha_spicata/mentha_spicata_germination_Mi6Y7dY.png"},
    {"plant": "mentha_spicata", "phase": GrowthState.GROWTH,      "url": "plants/mentha_spicata/mentha_spicata_growth_fFHtLuw.png"},
    {"plant": "mentha_spicata", "phase": GrowthState.MATURE,      "url": "plants/mentha_spicata/mentha_spicata_mature_iLVJ1ft.png"},
    {"plant": "mentha_spicata", "phase": GrowthState.FLOWERING,   "url": "plants/mentha_spicata/mentha_spicata_flowering_mV3u5qk.png"},
    {"plant": "mentha_spicata", "phase": GrowthState.DEAD,        "url": "plants/mentha_spicata/mentha_spicata_dead_hnYHu2o.png"},

    # --- rosa_canina & lavandula_angustifolia --- (pendiente, añade cuando subas las imágenes a S3)
]