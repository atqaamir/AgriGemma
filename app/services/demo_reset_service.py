"""Demo data: the startup forecast step and "Reset demo".

Reset demo puts the farm back to the fresh-start state on the demo date: reseed the demo
tables (users, fields, crops, tasks, plans, weather, notifications, chat history, AI
reports) and apply the calm forecast (no AI, no notifications), exactly as run.py's
bootstrap does. Vocabulary and rulebook tables are not touched.
"""
import logging

from app.extensions import db

logger = logging.getLogger(__name__)


def apply_startup_forecast():
    """Apply the forecast to every user's plan right after seeding (plan roll + forecast +
    plan task sync; no AI calls, no notifications), so a fresh start already shows the
    forecast-adjusted dates instead of waiting for the first simulator click / 5 AM job."""
    from app.agents.coordinator_agent import CoordinatorAgent
    from app.models.user import User
    coordinator = CoordinatorAgent()
    for user in User.query.order_by(User.id).all():
        try:
            result = coordinator.startup_forecast(user.id)
            logger.info("Startup forecast for user %s: %s", user.id,
                        {k: v.get("status") for k, v in result.items()})
        except Exception:
            db.session.rollback()
            logger.exception("Startup forecast failed for user %s — app starts with the seeded plan", user.id)


def reset_demo():
    """Reseed the demo data and apply the startup forecast; clears the active scenario."""
    from Test_Runs.seed_data import run as seed_data_run
    from Test_Runs.populate_seasonal_plan import run as populate_seasonal_plan_run
    from Test_Runs.populate_weekly_plan import run as populate_weekly_plan_run
    from app.services import demo_scenario_service

    seed_data_run()
    populate_seasonal_plan_run()
    populate_weekly_plan_run()
    apply_startup_forecast()
    demo_scenario_service.clear()
