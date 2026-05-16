from datetime import date, timedelta

from app.repositories.weather_repository import WeatherRepository


class WeatherService:

    def __init__(self):
        self.repo = WeatherRepository()

    # ------------------------------------------------------------------
    # Single-date queries
    # ------------------------------------------------------------------

    def get_for_date(self, for_date: date) -> list[dict]:
        """All regions for one date."""
        records = WeatherRepository.get_by_date(for_date)
        return [r.to_dict() for r in records]

    def get_for_region_and_date(self, region: str, for_date: date) -> dict | None:
        """Single region, single date."""
        record = WeatherRepository.get_by_region_and_date(region, for_date)
        return record.to_dict() if record else None

    # ------------------------------------------------------------------
    # 7-day queries  (start_date … start_date + 6)
    # ------------------------------------------------------------------

    def get_for_week(self, start_date: date) -> list[dict]:
        """All regions for the 7-day window starting on start_date."""
        end_date = start_date + timedelta(days=6)
        records = WeatherRepository.get_by_date_range(start_date, end_date)
        return [r.to_dict() for r in records]

    def get_for_region_and_week(self, region: str, start_date: date) -> list[dict]:
        """Single region, 7-day window."""
        end_date = start_date + timedelta(days=6)
        records = WeatherRepository.get_by_region_and_date_range(region, start_date, end_date)
        return [r.to_dict() for r in records]

    # ------------------------------------------------------------------
    # Arbitrary date-range query
    # ------------------------------------------------------------------

    def get_for_region_and_range(
        self, region: str, start_date: date, end_date: date
    ) -> list[dict]:
        records = WeatherRepository.get_by_region_and_date_range(region, start_date, end_date)
        return [r.to_dict() for r in records]

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create(self, data: dict) -> dict:
        record = WeatherRepository.create(data)
        return record.to_dict()

    def update(self, record_id: int, data: dict) -> dict | None:
        record = WeatherRepository.get_by_id(record_id)
        if record is None:
            return None
        updated = WeatherRepository.update(record, data)
        return updated.to_dict()

    def delete(self, record_id: int) -> bool:
        record = WeatherRepository.get_by_id(record_id)
        if record is None:
            return False
        WeatherRepository.delete(record)
        return True
