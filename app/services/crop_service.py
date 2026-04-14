def get_crop_health(crop):
    if crop.health_status == "good":
        return "Healthy"
    elif crop.health_status == "warning":
        return "Needs attention"
    return "At risk"