from http.client import responses

from app.agents.dashboard_agent import DashboardAgent
from app.agents.risk_agent import RiskAgent
from app.agents.planning_agent import PlanningAgent
from app.agents.advisory_agent import AdvisoryAgent
from app.agents.alert_agent import AlertAgent
from app.utils import enums_
from app.utils import execution_responses



class CoordinatorAgent:

    def __init__(self):
        self.planning_agent = PlanningAgent()
        self.risk_agent = RiskAgent()
        self.advisory_agent = AdvisoryAgent()
        self.alert_agent = AlertAgent()
        self.dashboard_agent = DashboardAgent()
        self.alert_agent = AlertAgent()

    def seasonal_planning(self, user_id):
        seasonal_planner_status = self.planning_agent.generate_seasonal_plan(user_id, tag="seasonal_planning ")
        if seasonal_planner_status == enums_.Status.SUCCESS:
            return execution_responses.ExecutionResponse.success("Seasonal planning completed")
        else:
            return execution_responses.ExecutionResponse.failure("Seasonal planning failed")
        
    def weekly_planning(self, user_id):
        weekly_planner_status = self.planning_agent.generate_weekly_plan(user_id, tag="weekly_planning ")
        if weekly_planner_status == enums_.Status.SUCCESS:
            return execution_responses.ExecutionResponse.success("Weekly planning completed")
        else:
            return execution_responses.ExecutionResponse.failure("Weekly planning failed")
        
    def task_generation(self, user_id):
        daily_planner_status = self.planning_agent.generate_daily_tasks(user_id, tag="daily_planning ")
        self.dashboard_agent.refresh_dashboard(user_id)
        if daily_planner_status == enums_.Status.SUCCESS:
            return execution_responses.ExecutionResponse.success("Daily planning completed")
        else:
            return execution_responses.ExecutionResponse.failure("Daily planning failed")

    def daily_update(self, user_id):
        risk_assessment_status, change = self.risk_agent.assess_risk(user_id, tag="risk_assessment ")
        
        if change == enums_.ChangeStatus.NO_CHANGE:
            # No change, proceed with existing plans
            return execution_responses.ExecutionResponse.success("Risk assesment completed with no change")
        elif change == enums_.ChangeStatus.NO_IMPACT:
            self.call_advisor(user_id)
            self.send_alert(user_id, tag = "weather_only") # Type = notification
            pass
        else:
            # Change detected with impact, trigger re-planning and advisory
            self.weekly_planning(user_id)
            self.task_generation(user_id)
            self.call_advisor(user_id)
            self.send_alert(user_id,  tag=(
                    "weekly" # Type = warning
                    if change == enums_.ChangeStatus.IMPACT_PLAN
                    else "daily"
                ))  # Type = danger
       

        self.dashboard_agent.refresh_dashboard(user_id)

        
        
        if risk_assessment_status == enums_.Status.SUCCESS:
            return execution_responses.ExecutionResponse.success("Risk assesment completed")
        else:
            return execution_responses.ExecutionResponse.failure("Risk assessment failed")

    def dashboard_refresh(self, user_id):
        dashboard_refresh_status =  self.dashboard_agent.refresh_dashboard(user_id)
        if dashboard_refresh_status == enums_.Status.SUCCESS:
            return execution_responses.ExecutionResponse.success("Dashboard update completed")
        else:
            return execution_responses.ExecutionResponse.failure("Dashboard update failed")

    def call_advisor(self, user_id):
        advisor_call_status = self.advisory_agent.generate_advisory(user_id, tag="advisory_generation ")
        if advisor_call_status == enums_.Status.SUCCESS:
            return execution_responses.ExecutionResponse.success("Advisor call completed")
        else:
            return execution_responses.ExecutionResponse.failure("Advisor call failed")

    def send_alert(self, user_id, tag):
        alert_status = self.alert_agent.generate_alerts(user_id, tag=tag)
        if alert_status == enums_.Status.SUCCESS:
            return execution_responses.ExecutionResponse.success("Alert update completed")
        else:
            return execution_responses.ExecutionResponse.failure("Alert update failed")


        