import json
from datetime import date
from pathlib import Path

from app.services.seasonal_planner_service import SeasonalPlannerService
from app.services.weekly_planner_service import WeeklyPlannerService

OUTPUT = Path(__file__).parent / "weekly_plan_output.json"

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
        "sowing":               "05/20/2026",   # ← "MM/DD/YYYY"
        "irrigation_frequency": None,           # ← int, e.g. 3
        # "irrigation_start_date": "",          # ← override cascade if needed
        # "fertilization_date":    "",          # ← override cascade if needed
        # "harvesting":            "",          # ← override cascade if needed
    },
    # ── Entry 1 : Cotton / Loamy / Groundwater ───────────────────────
    {
        "sowing":               "05/21/2026",   # ← "MM/DD/YYYY"
        "irrigation_frequency": None,           # ← int
    },
    # ── Entry 2 : Rice / Clay / River ────────────────────────────────
    {
        "sowing":               "05/18/2026",   # ← "MM/DD/YYYY"
        "irrigation_frequency": None,           # ← int
    },
]

# =============================================================================


def run(user_id: int = 1):
    active_plan = SeasonalPlannerService.get_active_plan(user_id)

    if active_plan is None:
        print(f"WARNING: No active seasonal plan found for user {user_id} — skipping entry updates.")
    else:
        entries = active_plan.entries
        for i, update_dict in enumerate(ENTRY_UPDATES):
            if i >= len(entries):
                print(f"WARNING: ENTRY_UPDATES[{i}] has no matching entry in the plan — skipping.")
                continue

            payload = {
                k: v for k, v in update_dict.items()
                if v is not None and v != ""
            }
            if not payload:
                print(f"  Entry {i} ({entries[i].id}): no changes — all values are empty/None.")
                continue

            SeasonalPlannerService.update_entry(entries[i].id, payload)
            print(f"  Entry {i} ({entries[i].id}) updated: {payload}")

    WeeklyPlannerService.generate_plan(user_id, WEEK_START)
    print(f"Weekly plan generated for user {user_id} — week starting {WEEK_START}")

    results = {"user_1_active_weekly_plan": WeeklyPlannerService.show_active_plan(user_id)}
    with open(OUTPUT, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Weekly plan output written to {OUTPUT}")
