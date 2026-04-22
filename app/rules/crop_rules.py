# Pure data — NO logic here

CROP_RULES = {
    "maize": {
        "sowing": {
            "rain_threshold_mm": 15,
            "temp_min": 20,
            "temp_max": 35
        },
        "irrigation": {
            "days_after_sowing": 7
        },
        "fertilizer": {
            "days_after_sowing": 15,
            "avoid_rain_above_mm": 10
        }
    }
}