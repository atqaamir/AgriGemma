from datetime import date

from app.extensions import db
from app.models.plan_event_override import PlanEventOverride

_SOURCE_RANK = {PlanEventOverride.SOURCE_FORECAST: 0, PlanEventOverride.SOURCE_FARMER: 1}


class PlanEventOverrideRepository:

    @staticmethod
    def get_applicable(entry_id: int, as_of: date) -> list[PlanEventOverride]:
        """Overrides that apply when building the plan for `as_of`, oldest → newest.

        As-of rule: farmer_completed with as_of_date <= as_of; forecast_shift with
        as_of_date < as_of (that day's own forecast decisions are recomputed, not
        re-applied). Order: as_of_date, then farmer over forecast, then id.
        """
        rows = PlanEventOverride.query.filter(
            PlanEventOverride.seasonal_plan_entry_id == entry_id,
            PlanEventOverride.as_of_date <= as_of,
        ).all()
        rows = [
            r for r in rows
            if r.source == PlanEventOverride.SOURCE_FARMER or r.as_of_date < as_of
        ]
        return sorted(rows, key=lambda r: (r.as_of_date, _SOURCE_RANK.get(r.source, 0), r.id))

    @staticmethod
    def get_farmer_sowing(entry_id: int, as_of: date) -> PlanEventOverride | None:
        """Latest farmer_completed sowing override on or before `as_of`, if any."""
        return (PlanEventOverride.query
                .filter(PlanEventOverride.seasonal_plan_entry_id == entry_id,
                        PlanEventOverride.event_type == "sowing",
                        PlanEventOverride.source == PlanEventOverride.SOURCE_FARMER,
                        PlanEventOverride.as_of_date <= as_of)
                .order_by(PlanEventOverride.as_of_date.desc(), PlanEventOverride.id.desc())
                .first())

    @staticmethod
    def get_forecast_for_day(entry_ids: list[int], as_of: date) -> list[PlanEventOverride]:
        if not entry_ids:
            return []
        return PlanEventOverride.query.filter(
            PlanEventOverride.seasonal_plan_entry_id.in_(entry_ids),
            PlanEventOverride.source == PlanEventOverride.SOURCE_FORECAST,
            PlanEventOverride.as_of_date == as_of,
        ).all()

    @staticmethod
    def get_by_task(task_id: int) -> list[PlanEventOverride]:
        return PlanEventOverride.query.filter_by(task_id=task_id).all()

    @staticmethod
    def create(data: dict) -> PlanEventOverride:
        row = PlanEventOverride(**data)
        db.session.add(row)
        db.session.commit()
        return row

    @staticmethod
    def update(row: PlanEventOverride, data: dict) -> PlanEventOverride:
        for key, value in data.items():
            setattr(row, key, value)
        db.session.commit()
        return row

    @staticmethod
    def delete_many(rows: list[PlanEventOverride]) -> int:
        for r in rows:
            db.session.delete(r)
        db.session.commit()
        return len(rows)

    @staticmethod
    def delete_all() -> None:
        PlanEventOverride.query.delete()
        db.session.commit()
