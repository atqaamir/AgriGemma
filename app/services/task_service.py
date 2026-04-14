def generate_tasks(crop, weather):
    tasks = []

    if weather.get("rain_expected"):
        tasks.append("Delay irrigation")

    if crop.get("stage") == "growth":
        tasks.append("Apply fertilizer")

    return tasks