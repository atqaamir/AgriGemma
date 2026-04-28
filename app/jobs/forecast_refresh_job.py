from app.services.field_service import FieldService
from app.services.forecast_service import ForecastService


class ForecastRefreshJob:
    @staticmethod
    def run() -> list[dict]:
        results = []

        payload = FieldService.get_active_fields_with_tasks()
        fields = payload["fields"]

        print(f"Found active fields with tasks: {len(fields)}")

        forecast_service = ForecastService()

        for field in fields:
            print(f"Refreshing forecast for field: {field.id}")

            refresh_result = forecast_service.refresh_forecasts(field.id)

            results.append({
                "field_id": field.id,
                "daily_refreshed": refresh_result["daily_refreshed"],
                "weekly_refreshed": refresh_result["weekly_refreshed"],
            })

        return results