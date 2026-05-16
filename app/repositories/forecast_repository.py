from datetime import date

from app.models.weather_forecast import WeatherForecast
from app.extensions import db


class ForecastRepository:

    @staticmethod
    def get_by_id(record_id: int) -> WeatherForecast | None:
        return WeatherForecast.query.get(record_id)

    @staticmethod
    def get_by_date(for_date: date) -> list[WeatherForecast]:
        return WeatherForecast.query.filter_by(date=for_date).all()

    @staticmethod
    def get_by_region_and_date(region: str, for_date: date) -> WeatherForecast | None:
        return WeatherForecast.query.filter_by(region=region, date=for_date).first()

    @staticmethod
    def get_by_region_and_date_range(
        region: str, start_date: date, end_date: date
    ) -> list[WeatherForecast]:
        return (
            WeatherForecast.query
            .filter(
                WeatherForecast.region == region,
                WeatherForecast.date >= start_date,
                WeatherForecast.date <= end_date,
            )
            .order_by(WeatherForecast.date)
            .all()
        )

    @staticmethod
    def get_by_date_range(start_date: date, end_date: date) -> list[WeatherForecast]:
        return (
            WeatherForecast.query
            .filter(
                WeatherForecast.date >= start_date,
                WeatherForecast.date <= end_date,
            )
            .order_by(WeatherForecast.region, WeatherForecast.date)
            .all()
        )

    @staticmethod
    def create(data: dict) -> WeatherForecast:
        record = WeatherForecast(**data)
        db.session.add(record)
        db.session.commit()
        return record

    @staticmethod
    def update(record: WeatherForecast, data: dict) -> WeatherForecast:
        for key, value in data.items():
            setattr(record, key, value)
        db.session.commit()
        return record

    @staticmethod
    def delete(record: WeatherForecast) -> None:
        db.session.delete(record)
        db.session.commit()

    # ------------------------------------------------------------------
    # Legacy helpers used by ForecastService (fetch-and-store flow)
    # ------------------------------------------------------------------

    @staticmethod
    def get_latest_daily(region: str, for_date: date) -> WeatherForecast | None:
        return (
            WeatherForecast.query
            .filter_by(region=region, date=for_date)
            .order_by(WeatherForecast.created_at.desc())
            .first()
        )

    @staticmethod
    def get_latest_weekly(region: str, n: int = 7) -> list[WeatherForecast]:
        return (
            WeatherForecast.query
            .filter_by(region=region)
            .order_by(WeatherForecast.date.desc())
            .limit(n)
            .all()
        )

    @staticmethod
    def save_forecast(region: str, daily_data: list[dict]) -> None:
        for day in daily_data:
            record = WeatherForecast(
                region=region,
                date=day["date"],
                avg_temperature_c=day.get("temperature_c") or day.get("avg_temperature_c"),
                rainfall_mm=day.get("precipitation_mm") or day.get("rainfall_mm"),
                wind_speed_kph=day.get("wind_speed_kph"),
                humidity=day.get("humidity"),
                sunlight_hours=day.get("sunlight_hours"),
            )
            db.session.add(record)
        db.session.commit()
