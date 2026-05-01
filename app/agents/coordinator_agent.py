import logging

from app.agents.dashboard_agent import DashboardAgent
from app.agents.risk_agent import RiskAgent
from app.agents.planning_agent import PlanningAgent
from app.agents.advisory_agent import AdvisoryAgent
from app.agents.alert_agent import AlertAgent
from app.agents.task_intelligence_agent import TaskIntelligenceAgent
from app.utils import enums_
from app.utils import execution_responses

logger = logging.getLogger(__name__)


class CoordinatorAgent:
    """
    Central orchestrator.  Owns all agent instances and decides which agents
    participate in each workflow.  Routes never call agents directly — they
    call the coordinator.
    """

    def __init__(self) -> None:
        self.planning_agent = PlanningAgent()
        self.risk_agent = RiskAgent()
        self.advisory_agent = AdvisoryAgent()
        self.alert_agent = AlertAgent()
        self.dashboard_agent = DashboardAgent()
        self.task_intelligence_agent = TaskIntelligenceAgent()

    # ── Task Intelligence ─────────────────────────────────────────────────────

    def generate_task_intelligence(self, user_id: int) -> dict:
        """
        Orchestrate AI task intelligence generation.
        Always returns a valid intelligence dict (fallback on failure).
        """
        try:
            return self.task_intelligence_agent.generate(user_id)
        except Exception as exc:
            logger.error("CoordinatorAgent: task intelligence failed (user=%s) — %s", user_id, exc)
            return {
                "summary": "Intelligence overview temporarily unavailable.",
                "priority_level": "medium",
                "recommendations": ["Review pending tasks manually."],
                "urgent_actions": [],
                "risks": [],
                "insights": [],
                "generated_at": "",
                "is_fallback": True,
            }

    # ── Planning workflows ────────────────────────────────────────────────────

    def seasonal_planning(self, user_id: int) -> dict:
        status = self.planning_agent.generate_seasonal_plan(user_id, tag="seasonal_planning")
        if status == enums_.Status.SUCCESS:
            return execution_responses.ExecutionResponse.success("Seasonal planning completed")
        return execution_responses.ExecutionResponse.failure("Seasonal planning failed")

    def weekly_planning(self, user_id: int) -> dict:
        status = self.planning_agent.generate_weekly_plan(user_id, tag="weekly_planning")
        if status == enums_.Status.SUCCESS:
            return execution_responses.ExecutionResponse.success("Weekly planning completed")
        return execution_responses.ExecutionResponse.failure("Weekly planning failed")

    def task_generation(self, user_id: int) -> dict:
        status = self.planning_agent.generate_daily_tasks(user_id, tag="daily_planning")
        self.dashboard_agent.refresh_dashboard(user_id)
        # Invalidate cached intelligence so the next request reflects new tasks
        self.task_intelligence_agent.invalidate_cache(user_id)
        if status == enums_.Status.SUCCESS:
            return execution_responses.ExecutionResponse.success("Task generation completed")
        return execution_responses.ExecutionResponse.failure("Task generation failed")

    # ── Daily update workflow ─────────────────────────────────────────────────

    def daily_update(self, user_id: int) -> dict:
        risk_status, change = self.risk_agent.assess_risk(user_id, tag="risk_assessment")

        if change == enums_.ChangeStatus.NO_CHANGE:
            return execution_responses.ExecutionResponse.success("Risk assessment completed — no change")

        if change == enums_.ChangeStatus.NO_IMPACT:
            self.call_advisor(user_id)
            self.send_alert(user_id, tag="weather_only")
        else:
            self.weekly_planning(user_id)
            self.task_generation(user_id)
            self.call_advisor(user_id)
            alert_tag = "weekly" if change == enums_.ChangeStatus.IMPACT_PLAN else "daily"
            self.send_alert(user_id, tag=alert_tag)

        self.dashboard_agent.refresh_dashboard(user_id)

        if risk_status == enums_.Status.SUCCESS:
            return execution_responses.ExecutionResponse.success("Daily update completed")
        return execution_responses.ExecutionResponse.failure("Daily update failed")

    # ── Utility workflows ─────────────────────────────────────────────────────

    def dashboard_refresh(self, user_id: int) -> dict:
        status = self.dashboard_agent.refresh_dashboard(user_id)
        if status == enums_.Status.SUCCESS:
            return execution_responses.ExecutionResponse.success("Dashboard refresh completed")
        return execution_responses.ExecutionResponse.failure("Dashboard refresh failed")

    def call_advisor(self, user_id: int) -> dict:
        status = self.advisory_agent.generate_advisory(user_id, tag="advisory_generation")
        if status == enums_.Status.SUCCESS:
            return execution_responses.ExecutionResponse.success("Advisory generated")
        return execution_responses.ExecutionResponse.failure("Advisory generation failed")

    def send_alert(self, user_id: int, tag: str) -> dict:
        status = self.alert_agent.generate_alerts(user_id, tag=tag)
        if status == enums_.Status.SUCCESS:
            return execution_responses.ExecutionResponse.success("Alert sent")
        return execution_responses.ExecutionResponse.failure("Alert dispatch failed")
