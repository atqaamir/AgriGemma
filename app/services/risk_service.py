from app.services.context_service import ContextService
class RiskAgent:
    @staticmethod
    def get_risk_context(field_id: str) -> dict:
        daily_forecast = ContextService().get_latest_daily_forecast(field_id)
        weekly_forecast = ContextService().get_latest_weekly_forecast(field_id)
    
    def assess_risk(self, user_id, tag="risk_assessment "):
        asses_risk_status = "Success"
        change_status = "No Change"
        return asses_risk_status, change_status