def generate_tasks(weather, crop):
    tasks = []

    if weather.get("rain_expected"):
        tasks.append({
            "title": "Delay irrigation",
            "priority": "high"
        })

    if crop.get("growth_stage") == "growth":
        tasks.append({
            "title": "Apply fertilizer",
            "priority": "medium"
        })

    return tasks