from app.services.weather_service import get_weather
from app.services.recommendation_service import get_recommendations
from app.services.task_service import generate_tasks
from app.services.alert_service import generate_alerts
from app.services.gemma_prompt_service import (
    build_recommendation_prompt,
    build_chat_prompt,
)
from app.services.mock_data_service import get_mock_soil_data, get_mock_crop_data


def build_dashboard_data(location: str, crop_name: str, field_name: str) -> dict:
    weather = get_weather(location)
    soil = get_mock_soil_data(field_name)
    crop = get_mock_crop_data(crop_name, field_name)

    recommendations = get_recommendations(weather, soil, crop)
    tasks = generate_tasks(weather, crop, soil)
    alerts = generate_alerts(weather, crop, soil)

    gemma_recommendation_prompt = build_recommendation_prompt(
        weather=weather,
        soil=soil,
        crop=crop
    )

    gemma_chat_example_prompt = build_chat_prompt(
        user_input="Should I irrigate today?",
        weather=weather,
        soil=soil,
        crop=crop
    )

    return {
        "farm_overview": {
            "field_name": field_name,
            "crop_name": crop["name"],
            "field_size_acres": crop["field_size_acres"],
            "planting_date": crop["planting_date"],
            "growth_stage": crop["growth_stage"],
        },
        "weather": weather,
        "soil": soil,
        "crop": crop,
        "tasks": tasks,
        "alerts": alerts,
        "recommendations": recommendations,
        "gemma_prompts": {
            "recommendation_prompt": gemma_recommendation_prompt,
            "chat_prompt_example": gemma_chat_example_prompt,
        }
    }