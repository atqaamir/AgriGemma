from app.models.seasonal_plan import SeasonalPlan, SeasonalPlanEntry
from app.extensions import db


class SeasonalPlanRepository:

    @staticmethod
    def create(data: dict) -> SeasonalPlan:
        plan = SeasonalPlan(**data)
        db.session.add(plan)
        db.session.commit()
        return plan

    @staticmethod
    def get_all() -> list[SeasonalPlan]:
        return SeasonalPlan.query.all()

    @staticmethod
    def get_by_id(plan_id: int) -> SeasonalPlan | None:
        return SeasonalPlan.query.get(plan_id)

    @staticmethod
    def get_by_user_id(user_id: int) -> list[SeasonalPlan]:
        return SeasonalPlan.query.filter_by(user_id=user_id).all()

    @staticmethod
    def get_active_by_user_id(user_id: int) -> SeasonalPlan | None:
        return SeasonalPlan.query.filter_by(user_id=user_id, currently_active=True).first()

    @staticmethod
    def update(plan: SeasonalPlan, data: dict) -> SeasonalPlan:
        for key, value in data.items():
            setattr(plan, key, value)
        db.session.commit()
        return plan

    @staticmethod
    def delete(plan: SeasonalPlan) -> None:
        db.session.delete(plan)
        db.session.commit()


class SeasonalPlanEntryRepository:

    @staticmethod
    def create(data: dict) -> SeasonalPlanEntry:
        entry = SeasonalPlanEntry(**data)
        db.session.add(entry)
        db.session.commit()
        return entry

    @staticmethod
    def get_by_id(entry_id: int) -> SeasonalPlanEntry | None:
        return SeasonalPlanEntry.query.get(entry_id)

    @staticmethod
    def get_by_plan_id(plan_id: int) -> list[SeasonalPlanEntry]:
        return SeasonalPlanEntry.query.filter_by(plan_id=plan_id).all()

    @staticmethod
    def update(entry: SeasonalPlanEntry, data: dict) -> SeasonalPlanEntry:
        for key, value in data.items():
            setattr(entry, key, value)
        db.session.commit()
        return entry

    @staticmethod
    def delete(entry: SeasonalPlanEntry) -> None:
        db.session.delete(entry)
        db.session.commit()
