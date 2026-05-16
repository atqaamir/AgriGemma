from datetime import date, timedelta

from app.models.weather import Weather
from app.extensions import db


class WeatherRepository:

    @staticmethod
    def get_by_id(record_id: int) -> Weather | None:
        return Weather.query.get(record_id)

    @staticmethod
    def get_by_date(for_date: date) -> list[Weather]:
        return Weather.query.filter_by(date=for_date).all()

    @staticmethod
    def get_by_region_and_date(region: str, for_date: date) -> Weather | None:
        return Weather.query.filter_by(region=region, date=for_date).first()

    @staticmethod
    def get_by_region_and_date_range(
        region: str, start_date: date, end_date: date
    ) -> list[Weather]:
        return (
            Weather.query
            .filter(
                Weather.region == region,
                Weather.date >= start_date,
                Weather.date <= end_date,
            )
            .order_by(Weather.date)
            .all()
        )

    @staticmethod
    def get_by_date_range(start_date: date, end_date: date) -> list[Weather]:
        return (
            Weather.query
            .filter(Weather.date >= start_date, Weather.date <= end_date)
            .order_by(Weather.region, Weather.date)
            .all()
        )

    @staticmethod
    def create(data: dict) -> Weather:
        record = Weather(**data)
        db.session.add(record)
        db.session.commit()
        return record

    @staticmethod
    def update(record: Weather, data: dict) -> Weather:
        for key, value in data.items():
            setattr(record, key, value)
        db.session.commit()
        return record

    @staticmethod
    def delete(record: Weather) -> None:
        db.session.delete(record)
        db.session.commit()
