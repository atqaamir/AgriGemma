from app.services.risk_service import RiskService

class RiskAgent:
    def assess_risk(self, user_id, tag="risk_assessment "):
        return RiskService().assess_risk(user_id, tag)