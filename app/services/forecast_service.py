class ForecastService:
    def __init__(self):
        pass

    def refresh_forecasts(self, field_id):
        """
        Pull latest weather data from provider and store it locally.
        Used by scheduled jobs.
        """

        daily = self._fetch_daily_from_provider(field_id)
        weekly = self._fetch_weekly_from_provider(field_id)

        # later: save to DB
        # WeatherRepository.save_daily(field_id, daily)
        # WeatherRepository.save_weekly(field_id, weekly)

        return {
            "field_id": field_id,
            "daily_refreshed": True,
            "weekly_refreshed": True,
            "daily": daily,
            "weekly": weekly
        }

    def get_latest_daily_forecast(self, field_id):
        """
        Return latest stored daily forecast for system usage.
        Used by planner/dashboard.
        """

        return {
            "field_id": field_id,
            "location": "Lahore",
            "date": "2026-06-12",
            "temperature_c": 25,
            "rain_mm": 18,
            "humidity": 82,
            "condition": "Heavy Rain"
        }

    def get_latest_weekly_forecast(self, field_id):
        """
        Return latest stored weekly forecast for planning/risk evaluation.
        """

        return {
            "field_id": field_id,
            "location": "Lahore",
            "days": [
                {"date": "2026-06-12", "rain_mm": 18, "temp_c": 25},
                {"date": "2026-06-13", "rain_mm": 22, "temp_c": 24},
                {"date": "2026-06-14", "rain_mm": 5, "temp_c": 28},
                {"date": "2026-06-15", "rain_mm": 0, "temp_c": 31},
            ]
        }

    def _fetch_daily_from_provider(self, field_id):
        """
        Mock external weather provider call.
        Replace later with real API call.
        """
        return {
            "date": "2026-06-12",
            "temperature_c": 25,
            "rain_mm": 18,
            "humidity": 82,
            "condition": "Heavy Rain"
        }

    def _fetch_weekly_from_provider(self, field_id):
        """
        Mock 7-day weather provider call.
        Replace later with real API call.
        """
        return [
            {"date": "2026-06-12", "rain_mm": 18, "temp_c": 25},
            {"date": "2026-06-13", "rain_mm": 22, "temp_c": 24},
            {"date": "2026-06-14", "rain_mm": 5, "temp_c": 28},
            {"date": "2026-06-15", "rain_mm": 0, "temp_c": 31},
        ]