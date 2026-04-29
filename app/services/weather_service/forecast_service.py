from ...repositories.forecast_repository import ForecastRepository

from weather_fetch_api import get_weather

from app.utils.enums_ import Region

from app.schemas.weather.current_weather_profile_schema import (
    DailyForecastSchema,
    WeeklyForecastResponseSchema,
)


class ForecastService:

    def __init__(self):

        self.forecast_repository = ForecastRepository()

        self.daily_forecast_schema = DailyForecastSchema()

        self.weekly_forecast_schema = WeeklyForecastResponseSchema()

    # =========================================================
    # DATABASE QUERY METHODS
    # =========================================================

    def get_latest_daily_forecast(self, region, date):
        """
        Return latest stored daily forecast for database query.
        Used by planner/dashboard.
        """

        forecast = self.forecast_repository.get_latest_daily(
            region,
            date
        )

        return self.daily_forecast_schema.dump(forecast)

    def get_latest_weekly_forecast(self, region, n=7):
        """
        Return latest stored weekly forecast for database query.
        Used by planner/dashboard.
        """

        forecasts = self.forecast_repository.get_latest_weekly(
            region,
            n
        )

        response = {
            "region": region,
            "total_days": len(forecasts),
            "forecasts": forecasts,
        }

        return self.weekly_forecast_schema.dump(response)

    # =========================================================
    # FETCH + STORE METHODS
    # =========================================================

    def fetch_and_store_daily_forecast(self, region, n=7):
        """
        Fetch forecast from weather provider,
        normalize response,
        then save in DB.
        """

        raw_weather_data = get_weather(region, n)

        normalized_forecast_data = (
            self._normalize_weather_api_response(
                raw_weather_data
            )
        )

        return self.forecast_repository.save_forecast(
            region,
            normalized_forecast_data
        )

    # =========================================================
    # INTERNAL HELPERS
    # =========================================================

    def _normalize_weather_api_response(
        self,
        weather_api_response
    ):
        """
        Convert external weather API response
        into internal forecast schema format.

        TODO:
        Implement provider-specific normalization logic later.

        Expected normalized format:

        [
            {
                "date": "2026-06-12",
                "temperature_c": 25,
                "precipitation_mm": 18,
                "wind_speed_kph": 15,
            }
        ]
        """

        # -----------------------------------------------------
        # TEMP DUMMY IMPLEMENTATION
        # -----------------------------------------------------

        normalized_data = []

        for item in weather_api_response.forecast:

            normalized_data.append({
                "date": item["date"],
                "temperature_c": item["temperature_c"],
                "precipitation_mm": item["precipitation_mm"],
                "wind_speed_kph": item["wind_speed_kph"],
            })

        return normalized_data