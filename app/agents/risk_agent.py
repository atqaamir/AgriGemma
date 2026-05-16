from datetime import date

from app.services.risk_service import RiskService


class RiskAgent:

    def assess_risk(
        self,
        user_id: int,
        tag: str = "risk_assessment",
        as_of_date: date = None,
    ) -> tuple:
        """Returns (Status, ChangeStatus, detail_dict)."""
        return RiskService().assess_risk(user_id, tag, as_of_date)

