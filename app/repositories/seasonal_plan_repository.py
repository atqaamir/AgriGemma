from app.models.seasonal_plan import SeasonalPlan
from app.extensions import db


class SeasonalPlanRepository:

    @staticmethod
    def create(data: dict) -> SeasonalPlan:
        seasonal_plan = SeasonalPlan(**data)
        db.session.add(seasonal_plan)
        db.session.commit()
        return seasonal_plan

    @staticmethod
    def get_all():
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
    def update(seasonal_plan: SeasonalPlan, data: dict) -> SeasonalPlan:
        for key, value in data.items():
            setattr(seasonal_plan, key, value)
        db.session.commit()
        return seasonal_plan

    @staticmethod
    def delete(seasonal_plan: SeasonalPlan) -> None:
        db.session.delete(seasonal_plan)
        db.session.commit()
