import logging
from datetime import date

from app.agents.dashboard_agent import DashboardAgent
from app.agents.risk_agent import RiskAgent
from app.agents.planning_agent import PlanningAgent
from app.agents.notification_agent import  NotificationAgent
from app.agents.intelligence_agent import TaskIntelligenceAgent
from app.utils import enums_
from app.utils import execution_responses
from app.utils import clock

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
        if status == enums_.Status.SUCCESS:
            return execution_responses.ExecutionResponse.success("Task generation completed")
        return execution_responses.ExecutionResponse.failure("Task generation failed")

    # ── Daily update workflow ─────────────────────────────────────────────────

    """ 5am daily update workflow — rolls the weekly plan forward, runs risk assessment, then triggers downstream workflows based on risk level changes. Always refreshes dashboard at the end. """
    def daily_update(self, user_id: int, as_of_date: date = None) -> dict:
        if as_of_date is None:
            as_of_date = clock.today()
        print(f"\n[CoordinatorAgent] Starting daily update for user={user_id} as_of_date={as_of_date}")

        # Roll the weekly plan: regenerate as_of_date..+6 from the (unmodified)
        # seasonal plan every run, so adjustments never compound. A failure here
        # is logged and reported but does not skip the rest of the update.
        plan_roll = self._roll_weekly_plan(user_id, as_of_date)

        risk_status, change, _ = self.risk_agent.assess_risk(user_id, tag="risk_assessment", as_of_date=as_of_date)
        print (f"[daily update] risk assessment completed with status={risk_status}, change={change} for user={user_id}")

        # Always apply the forecast to the plan (sowing window, forecast overrides).
        # No AI calls; the only notification is a sowing decision (once per crop,
        # on the day it happens, also on days without a plan impact).
        plan_update = self._apply_forecast_to_plan(user_id, as_of_date)

        # Plan tasks follow the re-planned week right away (also on a simulator click):
        # move / deactivate / reactivate, create missing ones for today and tomorrow.
        plan_tasks = self._sync_plan_tasks(user_id, as_of_date)

        if change == enums_.ChangeStatus.NO_CHANGE:
            result = execution_responses.ExecutionResponse.success("Risk assessment completed — no change")

        elif change == enums_.ChangeStatus.NO_IMPACT:
            self.send_notification(user_id, tag="weather_only")
            self.dashboard_refresh(user_id)
            result = execution_responses.ExecutionResponse.success("Daily update completed")
        else:
            if change == enums_.ChangeStatus.IMPACT_PLAN:
                self.update_planner(user_id, tag="impact_weekly", as_of_date=as_of_date)
            elif change == enums_.ChangeStatus.IMPACT_TASKS:
                self.update_planner(user_id, tag="impact_tasks", as_of_date=as_of_date)
            notification_tag = "weekly" if change == enums_.ChangeStatus.IMPACT_PLAN else "daily"
            self.send_change_notifications(user_id, tag=notification_tag)
            self.dashboard_refresh(user_id)
            result = execution_responses.ExecutionResponse.success("Daily update completed") if risk_status == enums_.Status.SUCCESS else execution_responses.ExecutionResponse.failure("Daily update failed")

        result["change_status"] = change.value
        result["plan_roll"] = plan_roll
        result["plan_update"] = plan_update
        result["plan_tasks"] = plan_tasks
        if plan_roll["status"] == "failed":
            result["message"] += f" (weekly plan roll failed: {plan_roll['error']})"
        if plan_update["status"] == "failed":
            result["message"] += f" (forecast plan update failed: {plan_update['error']})"
        return result

    def _sync_plan_tasks(self, user_id: int, as_of_date: date) -> dict:
        """Sync plan tasks with the weekly plan (no AI calls). Never raises."""
        try:
            from app.services.task_generation_service import TaskGenerationService
            summary = TaskGenerationService.sync_plan_tasks(user_id, as_of_date)
            return {"status": "success", **summary}
        except Exception as exc:
            from app.extensions import db
            db.session.rollback()
            logger.exception("Daily update: plan task sync FAILED for user=%s as_of_date=%s", user_id, as_of_date)
            return {"status": "failed", "error": f"{type(exc).__name__}: {exc}"}

    def _apply_forecast_to_plan(self, user_id: int, as_of_date: date) -> dict:
        """Run the forecast re-plan (update_plan) on every daily update. Never raises."""
        try:
            status = self.planning_agent.apply_forecast(user_id, as_of_date)
            if status == enums_.Status.SUCCESS:
                return {"status": "success"}
            error = "update_plan failed (no active weekly plan?)"
            logger.error("Daily update: forecast plan update FAILED for user=%s: %s", user_id, error)
        except Exception as exc:
            from app.extensions import db
            db.session.rollback()
            error = f"{type(exc).__name__}: {exc}"
            logger.exception("Daily update: forecast plan update FAILED for user=%s as_of_date=%s",
                             user_id, as_of_date)
        return {"status": "failed", "error": error}

    def _roll_weekly_plan(self, user_id: int, as_of_date: date) -> dict:
        """Regenerate the weekly plan for as_of_date..as_of_date+6. Never raises."""
        try:
            status = self.planning_agent.generate_weekly_plan(
                user_id, tag="daily_roll", week_start_date=as_of_date
            )
            if status == enums_.Status.SUCCESS:
                return {"status": "success"}
            error = "generate_plan returned no plan"
        except Exception as exc:
            from app.extensions import db
            db.session.rollback()   # keep the session usable for the rest of the update
            error = f"{type(exc).__name__}: {exc}"
            logger.exception(
                "Daily update: weekly plan roll FAILED for user=%s as_of_date=%s — "
                "continuing with risk check", user_id, as_of_date,
            )
        else:
            logger.error(
                "Daily update: weekly plan roll FAILED for user=%s as_of_date=%s: %s — "
                "continuing with risk check", user_id, as_of_date, error,
            )
        return {"status": "failed", "error": error}

    # ── Utility workflows ─────────────────────────────────────────────────────

    def dashboard_refresh(self, user_id: int) -> dict:
        status = self.dashboard_agent.refresh_dashboard(user_id)
        if status == enums_.Status.SUCCESS:
            return execution_responses.ExecutionResponse.success("Dashboard refresh completed")
        return execution_responses.ExecutionResponse.failure("Dashboard refresh failed")

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

