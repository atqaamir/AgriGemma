from flask import Blueprint, jsonify, request
from app.services.ai_model_service.Gemma.gemma_prompt_service import build_chat_prompt
from app.services.mock_data_service.mock_data_service import get_mock_soil_data, get_mock_crop_data
from app.services.weather_service.weather_service import get_weather

chatbot_bp = Blueprint("chatbot", __name__)


@chatbot_bp.route("/chatbot", methods=["POST"])
def chatbot():
    data = request.get_json() or {}
    user_input = data.get("message", "What should I do today?")
    location = data.get("location", "Lahore")
    crop_name = data.get("crop", "Wheat")
    field_name = data.get("field", "North Field")

    weather = get_weather(location)
    soil = get_mock_soil_data(field_name)
    crop = get_mock_crop_data(crop_name, field_name)

    prompt = build_chat_prompt(
        user_input=user_input,
        weather=weather,
        soil=soil,
        crop=crop
    )

    return jsonify({
        "message": "Chat prompt generated successfully",
        "prompt": prompt
    }), 200