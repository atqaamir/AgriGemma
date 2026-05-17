import logging
from datetime import date

from app.agents.dashboard_agent import DashboardAgent
from app.agents.risk_agent import RiskAgent
from app.agents.planning_agent import PlanningAgent
from app.agents.notification_agent import  NotificationAgent
from app.agents.intelligence_agent import TaskIntelligenceAgent
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
        self.notification_agent = NotificationAgent()
        self.dashboard_agent = DashboardAgent()
        self.task_intelligence_agent = TaskIntelligenceAgent()

    # ── Task Intelligence ─────────────────────────────────────────────────────

    def generate_task_intelligence(self, user_id: int) -> dict:
        """
        Orchestrate AI task intelligence generation for tasks and dashboard summaries.
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

    def update_planner(self, user_id: int, tag: str, as_of_date=None) -> dict:
        status = self.planning_agent.daily_update(user_id, as_of_date=as_of_date, tag=tag)
        if status == enums_.Status.SUCCESS:
            return execution_responses.ExecutionResponse.success(f"Plan updated — {tag}")
        return execution_responses.ExecutionResponse.failure("Plan update failed")

    """ 7pm next day task generation — called by daily update workflow and can be exposed for manual trigger if needed """
    def task_generation(self, user_id: int) -> dict:
        status = self.planning_agent.generate_daily_tasks(user_id, tag="daily_planning")
        self.dashboard_refresh(user_id)
        # # Invalidate cached intelligence so the next request reflects new tasks
        # self.task_intelligence_agent.invalidate_cache(user_id)
        if status == enums_.Status.SUCCESS:
            return execution_responses.ExecutionResponse.success("Task generation completed")
        return execution_responses.ExecutionResponse.failure("Task generation failed")

    # ── Daily update workflow ─────────────────────────────────────────────────

    """ 5am daily update workflow — runs risk assessment, then triggers downstream workflows based on risk level changes. Always refreshes dashboard at the end. """
    def daily_update(self, user_id: int, as_of_date: date = None) -> dict:
        print(f"\n[CoordinatorAgent] Starting daily update for user={user_id} as_of_date={as_of_date}")
        risk_status, change, _ = self.risk_agent.assess_risk(user_id, tag="risk_assessment", as_of_date=as_of_date)
        print (f"[daily update] risk assessment completed with status={risk_status}, change={change} for user={user_id}")

        if change == enums_.ChangeStatus.NO_CHANGE:
            result = execution_responses.ExecutionResponse.success("Risk assessment completed — no change")
     
        elif change == enums_.ChangeStatus.NO_IMPACT:
            # self.call_intelligence(user_id, tag="critical_task_overview")
            self.send_notification(user_id, tag="weather_only")
            self.dashboard_refresh(user_id)
            result = execution_responses.ExecutionResponse.success("Daily update completed")
        else:
            if change == enums_.ChangeStatus.IMPACT_PLAN:
                self.update_planner(user_id, tag="impact_weekly", as_of_date=as_of_date)
            elif change == enums_.ChangeStatus.IMPACT_TASKS:
                self.update_planner(user_id, tag="impact_tasks", as_of_date=as_of_date)
            # self.call_intelligence(user_id, tag="critical_task_overview")
            notification_tag = "weekly" if change == enums_.ChangeStatus.IMPACT_PLAN else "daily"
            self.send_change_notifications(user_id, tag=notification_tag)
            self.dashboard_refresh(user_id)
            result = execution_responses.ExecutionResponse.success("Daily update completed") if risk_status == enums_.Status.SUCCESS else execution_responses.ExecutionResponse.failure("Daily update failed")

        result["change_status"] = change.value
        return result

    # ── Utility workflows ─────────────────────────────────────────────────────

    def dashboard_refresh(self, user_id: int) -> dict:
        status = self.dashboard_agent.refresh_dashboard(user_id)
        if status == enums_.Status.SUCCESS:
            return execution_responses.ExecutionResponse.success("Dashboard refresh completed")
        return execution_responses.ExecutionResponse.failure("Dashboard refresh failed")

    def call_intelligence(self, user_id: int, tag: str) -> dict:
        self.task_intelligence_agent.generate(user_id, tag=tag)
        return execution_responses.ExecutionResponse.success(f"{tag.replace('_', ' ').title()} generated")

    def send_notification(self, user_id: int, tag: str) -> dict:
        status = self.notification_agent.generate_notifications(user_id, tag=tag)
        if status == enums_.Status.SUCCESS:
            return execution_responses.ExecutionResponse.success("Notification sent")
        return execution_responses.ExecutionResponse.failure("Notification dispatch failed")

    def send_change_notifications(self, user_id: int, tag: str) -> dict:
        """Collects change data first, then creates both the alert and change_summary popup in one Ollama call."""
        status = self.notification_agent.generate_change_notifications(user_id, tag=tag)
        if status == enums_.Status.SUCCESS:
            return execution_responses.ExecutionResponse.success("Change notifications sent")
        return execution_responses.ExecutionResponse.failure("Change notification dispatch failed")

