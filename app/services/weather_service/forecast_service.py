import logging
from datetime import datetime

from ...repositories.forecast_repository import ForecastRepository

from .weather_fetch_api import get_weather, get_yearly_climate, get_monthly_climate

from app.utils.enums_ import Region

from app.schemas.weather.weekly_forecast import (
    DailyForecastSchema,
    WeeklyForecastResponseSchema,
)

logger = logging.getLogger(__name__)


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

    @staticmethod
    def _resolve_location(user_id: int = None) -> str:
        location = "Lahore"
        if user_id is not None:
            try:
                from app.services.domain_service.user_service import UserService
                user = UserService.get_user_by_id(user_id)
                if user and getattr(user, "location", None):
                    location = user.location
            except Exception:
                pass
        return location

    @staticmethod
    def get_current_summary(user_id: int = None) -> dict:
        """Return normalized current weather and forecast context for the chatbot."""
        location = ForecastService._resolve_location(user_id)
        try:
            raw_weather_data = get_weather(location)
            return ForecastService._normalize_current_summary(raw_weather_data)
        except Exception as exc:
            logger.warning("ForecastService: failed to fetch current weather for %s — %s", location, exc)
            return {}

    @staticmethod
    def get_climate_context(user_id: int = None) -> dict:
        """Return current-month, next two months, and full yearly climate profile."""
        location = ForecastService._resolve_location(user_id)
        try:
            now = datetime.now()
            current_month = now.month
            next_month    = (current_month % 12) + 1
            month_after   = (next_month   % 12) + 1

            yearly  = get_yearly_climate(location)
            current = get_monthly_climate(location, current_month)
            nxt     = get_monthly_climate(location, next_month)
            after   = get_monthly_climate(location, month_after)

            return {
                "location": location,
                "region": yearly["region"],
                "climate_type": yearly["climate_type"],
                "current_month": current,
                "next_month": nxt,
                "month_after": after,
                "yearly": yearly["months"],
                "best_sowing_months": yearly["best_sowing_months"],
                "best_harvest_months": yearly["best_harvest_months"],
                "monsoon_months": yearly["monsoon_months"],
                "heat_peak_months": yearly["heat_peak_months"],
            }
        except Exception as exc:
            logger.warning("ForecastService: climate context failed for %s — %s", location, exc)
            return {}

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
        forecast_items = getattr(weather_api_response, "forecast", None) or weather_api_response.get("forecast", [])

        for item in forecast_items:

            normalized_data.append({
                "date": item["date"],
                "temperature_c": item["temperature_c"],
                "precipitation_mm": item["precipitation_mm"],
                "wind_speed_kph": item["wind_speed_kph"],
            })

        return normalized_data

    @staticmethod
    def _normalize_current_summary(weather_api_response):
        if not weather_api_response:
            return {}

        current = weather_api_response.get("current") or {}
        forecast = getattr(weather_api_response, "forecast", None) or weather_api_response.get("forecast", []) or []

        def _normalize_forecast_item(item):
            rain_chance = item.get("rain_chance")
            if rain_chance is not None:
                if rain_chance >= 60:
                    condition = "Rainy"
                elif rain_chance >= 20:
                    condition = "Cloudy"
                else:
                    condition = "Sunny"
            else:
                condition = item.get("condition") or "Unknown"

            return {
                "day": item.get("day") or item.get("date"),
                "condition": item.get("condition") or condition,
                "max_temp_c": item.get("max_temp_c") or item.get("temperature_c") or item.get("max_temp"),
                "min_temp_c": item.get("min_temp_c") or item.get("temperature_c") or item.get("min_temp"),
                "rain_chance": rain_chance if rain_chance is not None else item.get("rain_chance", 0),
            }

        temp = current.get("temp") or current.get("temperature_c") or current.get("temperature")
        humidity = current.get("humidity")
        rainfall = current.get("rainfall_mm") if current.get("rainfall_mm") is not None else current.get("precipitation_mm", 0)

        return {
            "current": {
                "temp": temp,
                "condition": current.get("condition") or current.get("weather_condition") or "Unknown",
                "humidity": humidity,
                "rainfall_mm": rainfall,
                "wind_kph": current.get("wind_kph") or current.get("wind_speed_kph"),
            },
            "forecast": [
                _normalize_forecast_item(item)
                for item in forecast
            ],
            "rain_expected": weather_api_response.get("rain_expected", False),
            "heatwave_risk": weather_api_response.get("heatwave_risk", False),
        }
