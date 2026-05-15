import sys
import json
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import create_app
from app.services.seasonal_planner_service import SeasonalPlannerService
from app.services.weekly_planner_service import WeeklyPlannerService

app = create_app()

SEASONAL_OUTPUT = Path(__file__).parent / "seasonal_plan_tests.json"
WEEKLY_OUTPUT   = Path(__file__).parent / "weekly_plan_tests.json"

# =============================================================================
#  FILL IN before running
# =============================================================================

# Week to generate the plan for (Monday of the target week)
WEEK_START = date(2026, 5, 18)                        # ← fill in

# One dict per entry in user 1's active seasonal plan.
# Entries are in insertion order: Maize, Cotton, Rice (from populate_seasonal_plan.py).
# Rules:
#   - "sowing" change cascades the same delta to irrigation_start_date,
#     fertilization_date, and harvesting automatically.
#   - To override a cascaded date explicitly, uncomment and set it here.
#   - Set a key to None (or omit it) to leave that field unchanged.
ENTRY_UPDATES = [
    # ── Entry 0 : Maize / Loamy / Groundwater ────────────────────────
    {
        "sowing":               "05/20/2026",          # ← "MM/DD/YYYY"
        "irrigation_frequency": None,        # ← int, e.g. 3
        # "irrigation_start_date": "",       # ← override cascade if needed
        # "fertilization_date":    "",       # ← override cascade if needed
        # "harvesting":            "",       # ← override cascade if needed
    },
    # ── Entry 1 : Cotton / Loamy / Groundwater ───────────────────────
    {
        "sowing":               "05/21/2026",          # ← "MM/DD/YYYY"
        "irrigation_frequency": None,        # ← int
    },
    # ── Entry 2 : Rice / Clay / River ────────────────────────────────
    {
        "sowing":               "05/18/2026",          # ← "MM/DD/YYYY"
        "irrigation_frequency": None,        # ← int
    },
]

# =============================================================================

with app.app_context():

    # ── Step 1: Update seasonal plan entries for user 1 ──────────────────────
    active_plan = SeasonalPlannerService.get_active_plan(1)

    if active_plan is None:
        print("WARNING: No active seasonal plan found for user 1 — skipping entry updates.")
    else:
        entries = active_plan.entries
        for i, update_dict in enumerate(ENTRY_UPDATES):
            if i >= len(entries):
                print(f"WARNING: ENTRY_UPDATES[{i}] has no matching entry in the plan — skipping.")
                continue

            # Strip keys whose value is None or empty string — don't overwrite with blanks
            payload = {
                k: v for k, v in update_dict.items()
                if v is not None and v != ""
            }
            if not payload:
                print(f"  Entry {i} ({entries[i].id}): no changes — all values are empty/None.")
                continue

            SeasonalPlannerService.update_entry(entries[i].id, payload)
            print(f"  Entry {i} ({entries[i].id}) updated: {payload}")

    # ── Step 2: Generate weekly plan for user 1 ───────────────────────────────
    WeeklyPlannerService.generate_plan(1, WEEK_START)
    print(f"Weekly plan generated for user 1 — week starting {WEEK_START}")

    # ── Step 3: Collect output ────────────────────────────────────────────────
    seasonal_results = {
        "user_1_active_seasonal_plan": SeasonalPlannerService.show_active_plan(1),
    }

    weekly_results = {
        "user_1_active_weekly_plan": WeeklyPlannerService.show_active_plan(1),
    }

# ── Write JSON output ─────────────────────────────────────────────────────────
with open(SEASONAL_OUTPUT, "w") as f:
    json.dump(seasonal_results, f, indent=2)
print(f"Seasonal plan results written to {SEASONAL_OUTPUT}")

with open(WEEKLY_OUTPUT, "w") as f:
    json.dump(weekly_results, f, indent=2)
print(f"Weekly plan results written to {WEEKLY_OUTPUT}")
