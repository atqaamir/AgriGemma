from flask import Blueprint, jsonify, request
from app.services.weather_service.weather_service import get_weather

weather_bp = Blueprint("weather", __name__)


@weather_bp.route("/", methods=["GET"])
def weather():
    location = request.args.get("location", "Lahore")
    return jsonify(get_weather(location)), 200