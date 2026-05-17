import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app
from app.services.weekly_planning_service.weekly_planner_service import WeeklyPlannerService
from app.agents.coordinator_agent import CoordinatorAgent
from app.services.domain_service.notification_service import NotificationService

app = create_app()

# user[0] Ahmad Khan  (Punjab)    
# user[1] Ali Raza    (Sindh)     
# user[2] Faisal      (Islamabad) 
TEST_USERS = [1]
WEEK_START = date(2026, 5, 18)
AS_OF_DATE = date(2026, 5, 18)

# ── Mode ──────────────────────────────────────────────────────────────────────
# "coordinator" → full daily_update pipeline (needs a weather change to trigger notifications)
# "notifications" → directly create all notification types, skipping the risk gate
MODE = "coordinator"

with app.app_context():
    svc = NotificationService()

    for user_id in TEST_USERS:
        print(f"\n{'═' * 52}")
        print(f"  User {user_id}  |  mode={MODE}")
        print(f"{'═' * 52}")

        if MODE == "notifications":
            # ── Direct notification test — bypasses coordinator/risk gate ──
            for tag in ("weather_only", "weekly", "daily", "change_summary"):
                status = svc.generate_notifications(user_id, tag=tag)
                print(f"  {tag:<20} → {status.value}")

        elif MODE == "coordinator":
            coordinator = CoordinatorAgent()

            # Ensure a weekly plan exists
            active = WeeklyPlannerService.get_active_plan(user_id)
            if not active or active.week_start_date != WEEK_START:
                print(f"  Generating weekly plan for user {user_id}...")
                WeeklyPlannerService.generate_plan(user_id, WEEK_START)

            result = coordinator.daily_update(user_id=user_id, as_of_date=AS_OF_DATE)

            print(f"  Change status   : {result['change_status']}")
            print(f"  Execution status: {result['execution_status']}")
            print(f"  Message         : {result.get('message', '—')}")

    print(f"\n{'═' * 52}\n")
