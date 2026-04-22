from app.services.field_service import field_service
from app.services.forecast_service import forecast_service


class ForecastRefreshJob:
    @staticmethod
    def run() -> list[dict]:
        results = []
        active_fields = field_service.get_active_fields()

        for field in active_fields:
            refreshed = forecast_service.refresh_forecasts(field["id"])
            results.append({
                "field_id": field["id"],
                "forecast_refreshed": refreshed,
            })

        return results