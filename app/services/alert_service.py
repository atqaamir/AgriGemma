def generate_alerts(weather, crop, soil):
    alerts = []

    # 🌦️ Weather-based alerts
    temp = weather.get("current", {}).get("temperature_c", 0)
    rainfall = weather.get("current", {}).get("precip_mm", 0)

    if temp > 38:
        alerts.append({
            "message": "Heatwave risk: high temperature may damage crops",
            "level": "high",
            "type": "weather"
        })

    if rainfall > 20:
        alerts.append({
            "message": "Heavy rain expected: risk of waterlogging",
            "level": "medium",
            "type": "weather"
        })

    # 🌾 Soil-based alerts
    moisture = soil.get("moisture_percent", 50)
    soil_temp = soil.get("temperature_c", 25)

    if moisture < 25:
        alerts.append({
            "message": "Low soil moisture: crops may suffer water stress",
            "level": "high",
            "type": "soil"
        })

    if moisture > 85:
        alerts.append({
            "message": "Soil too wet: risk of root damage or fungal disease",
            "level": "medium",
            "type": "soil"
        })

    if soil_temp > 35:
        alerts.append({
            "message": "High soil temperature: possible root stress",
            "level": "medium",
            "type": "soil"
        })

    # 🌱 Crop-based alerts
    growth_stage = (crop.get("growth_stage") or "").lower()
    health_status = (crop.get("health_status") or "").lower()

    if health_status == "warning":
        alerts.append({
            "message": "Crop health warning: needs attention",
            "level": "medium",
            "type": "crop"
        })

    if health_status == "risk":
        alerts.append({
            "message": "Crop at risk: immediate action required",
            "level": "high",
            "type": "crop"
        })

    if growth_stage == "flowering" and temp > 35:
        alerts.append({
            "message": "High heat during flowering: yield may be affected",
            "level": "high",
            "type": "crop"
        })

    # 🧠 Optional: remove duplicates
    unique_alerts = []
    seen = set()

    for alert in alerts:
        if alert["message"] not in seen:
            unique_alerts.append(alert)
            seen.add(alert["message"])

    return unique_alerts