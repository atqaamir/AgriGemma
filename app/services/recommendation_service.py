def get_recommendations(weather, soil, crop):
    recommendations = []

    if weather.get("temperature") > 35:
        recommendations.append("Irrigate early morning")

    if soil.get("moisture") < 30:
        recommendations.append("Increase watering")

    return recommendations

    from .gemma_service import ask_gemma

def generate_farming_advice(weather, soil, crop):
    prompt = f"""
    You are an agricultural expert.

    Weather: {weather}
    Soil: {soil}
    Crop: {crop}

    Suggest:
    - Tasks
    - Alerts
    - Recommendations

    Keep it simple for farmers.
    """

    return ask_gemma(prompt)