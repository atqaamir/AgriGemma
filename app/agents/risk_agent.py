from app.services.forecast_service import forecast_service
from app.services.soil_service import soil_service
from app.services.crop_health_service import crop_health_service
from app.services.alert_service import alert_service


class RiskAgent:
    @staticmethod
    def get_risk_context(field_id: str) -> dict:
        daily_forecast = forecast_service.get_latest_daily_forecast(field_id)
        weekly_forecast = forecast_service.get_latest_weekly_forecast(field_id)
        soil_condition = soil_service.get_soil_condition(field_id)
        crop_health = crop_health_service.get_crop_health(field_id)
        alerts = alert_service.get_active_alerts(field_id)

        return {
            "daily_forecast": daily_forecast,
            "weekly_forecast": weekly_forecast,
            "soil_condition": soil_condition,
            "crop_health": crop_health,
            "alerts": alerts,
        }