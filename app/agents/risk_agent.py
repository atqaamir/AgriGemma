from app.services.weather_service.forecast_service import ForecastService
from app.services.context_service.soil_service import SoilService
from app.services.crop_health_service import CropHealthService
from app.services.alert_service import AlertService 


class RiskAgent:
    @staticmethod
    def get_risk_context(field_id: str) -> dict:
        daily_forecast = ForecastService().get_latest_daily_forecast(field_id)
        weekly_forecast = ForecastService().get_latest_weekly_forecast(field_id)
        soil_condition = SoilService().get_soil_condition(field_id)
        crop_health = CropHealthService().get_crop_health(field_id)
        alerts = AlertService().get_active_alerts(field_id)

        return {
            "daily_forecast": daily_forecast,
            "weekly_forecast": weekly_forecast,
            "soil_condition": soil_condition,
            "crop_health": crop_health,
            "alerts": alerts,
        }