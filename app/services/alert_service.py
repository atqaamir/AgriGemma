def generate_alerts(weather):
    alerts = []

    temp = weather.get("current", {}).get("temp_c", 0)

    if temp > 38:
        alerts.append({
            "message": "Heatwave risk",
            "level": "high"
        })

    if weather.get("current", {}).get("precip_mm", 0) > 20:
        alerts.append({
            "message": "Heavy rain expected",
            "level": "medium"
        })

    return alerts