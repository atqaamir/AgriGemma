import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import create_app
from app.services.seasonal_planner_service import SeasonalPlannerService

app = create_app()

OUTPUT_FILE = Path(__file__).parent / "seasonal_plan_tests.json"

with app.app_context():
    plan_5 = SeasonalPlannerService.show_plan(5)
    plan_6 = SeasonalPlannerService.show_plan(6)

results = {
    "plan_5": plan_5,
    "plan_6": plan_6,
}

with open(OUTPUT_FILE, "w") as f:
    json.dump(results, f, indent=2)

print(f"Results written to {OUTPUT_FILE}")
