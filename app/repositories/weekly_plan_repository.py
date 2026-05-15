from app.models.weekly_plan import WeeklyPlan, WeeklyPlanEntry
from app.extensions import db


class WeeklyPlanRepository:

    @staticmethod
    def create(data: dict) -> WeeklyPlan:
        plan = WeeklyPlan(**data)
        db.session.add(plan)
        db.session.commit()
        return plan

    @staticmethod
    def get_all() -> list[WeeklyPlan]:
        return WeeklyPlan.query.all()

    @staticmethod
    def get_by_id(plan_id: int) -> WeeklyPlan | None:
        return WeeklyPlan.query.get(plan_id)

    @staticmethod
    def get_by_user_id(user_id: int) -> list[WeeklyPlan]:
        return WeeklyPlan.query.filter_by(user_id=user_id).all()

    @staticmethod
    def get_active_by_user_id(user_id: int) -> WeeklyPlan | None:
        return WeeklyPlan.query.filter_by(user_id=user_id, currently_active=True).first()

    @staticmethod
    def update(plan: WeeklyPlan, data: dict) -> WeeklyPlan:
        for key, value in data.items():
            setattr(plan, key, value)
        db.session.commit()
        return plan

    @staticmethod
    def delete(plan: WeeklyPlan) -> None:
        db.session.delete(plan)
        db.session.commit()


class WeeklyPlanEntryRepository:

    @staticmethod
    def create(data: dict) -> WeeklyPlanEntry:
        entry = WeeklyPlanEntry(**data)
        db.session.add(entry)
        db.session.commit()
        return entry

    @staticmethod
    def get_by_id(entry_id: int) -> WeeklyPlanEntry | None:
        return WeeklyPlanEntry.query.get(entry_id)

    @staticmethod
    def get_by_plan_id(plan_id: int) -> list[WeeklyPlanEntry]:
        return WeeklyPlanEntry.query.filter_by(weekly_plan_id=plan_id).all()

    @staticmethod
    def update(entry: WeeklyPlanEntry, data: dict) -> WeeklyPlanEntry:
        for key, value in data.items():
            setattr(entry, key, value)
        db.session.commit()
        return entry

    @staticmethod
    def delete(entry: WeeklyPlanEntry) -> None:
        db.session.delete(entry)
        db.session.commit()
