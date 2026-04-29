from flask import Blueprint, request
from marshmallow import ValidationError

from app.services.weather_service import ForecastService

forecasts_bp = Blueprint("forecasts_bp", __name__)



from flask import request


@forecasts_bp.route("/forecasts/<string:region>", methods=["GET"])
def get_forecasts(region):

    n = request.args.get("days", default=3, type=int)

    return ForecastService.get_latest_weekly_forecast(
        region,
        n
    )
