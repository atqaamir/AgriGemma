import json
from datetime import date, timedelta
from pathlib import Path

from app.extensions import db
from app.models.weekly_plan import WeeklyPlan, WeeklyPlanEntry
from app.services.seasonal_planner_service import SeasonalPlannerService
from app.services.weekly_planning_service.weekly_planner_service import WeeklyPlannerService

OUTPUT = Path(__file__).parent / "weekly_plan_output.json"

# =============================================================================
#  FILL IN before running
# =============================================================================

# Week for the initial weekly plan: Monday of the current week.
_today = date.today()
WEEK_START = _today - timedelta(days=_today.weekday())


def _from_today(offset: int) -> str:
    """Date `offset` days after today, in the "MM/DD/YYYY" format update_entry expects.

    Sowing dates are relative to today (not WEEK_START) so they are never in the past
    and always fall inside the week the Weather Change Simulator builds from today.
    """
    return (_today + timedelta(days=offset)).strftime("%m/%d/%Y")

# One dict per entry in user 1's active seasonal plan.
# Entries are in insertion order: Maize, Cotton, Rice (from populate_seasonal_plan.py).
# Rules:
#   - "sowing" change cascades the same delta to irrigation_start_date,
#     fertilization_date, and harvesting automatically.
#   - To override a cascaded date explicitly, uncomment and set it here.
#   - Set a key to None (or omit it) to leave that field unchanged.
ENTRY_UPDATES = [
    # ── Entry 0 : Maize / Loamy / Groundwater ────────────────────────
    # field_id=1  →  North Field Alpha, Punjab (~15°C cold spell)
    #                temperature band "15-20" → cold-stress sowing adjustment
    {
        "sowing":               _from_today(1), # tomorrow
        "irrigation_frequency": None,           # ← int, e.g. 3
        "field_id":             1,              # North Field Alpha — Punjab, Pakistan
        # "irrigation_start_date": "",          # ← override cascade if needed
        # "fertilization_date":    "",          # ← override cascade if needed
        # "harvesting":            "",          # ← override cascade if needed
    },
    # ── Entry 1 : Cotton / Loamy / Groundwater ───────────────────────
    {
        "sowing":               _from_today(2), # today + 2 days
        "irrigation_frequency": None,           # ← int
    },
    # ── Entry 2 : Rice / Sandy / River ───────────────────────────────
    # Currently "Not Feasible" (Rice on Sandy soil) → skipped in run(), so no
    # dates are set. Kept so it applies if the seasonal plan makes it feasible.
    # field_id=2  →  East Creek Basin, Sindh (~34°C heat scenario)
    #                temperature band "30-40" → heat-stress sowing adjustment
    {
        "sowing":               _from_today(0), # today
        "irrigation_frequency": None,           # ← int
        "field_id":             2,              # East Creek Basin — Sindh, Pakistan
    },
]

# =============================================================================


def run(user_id: int = 1):
    WeeklyPlanEntry.query.delete()
    WeeklyPlan.query.delete()
    db.session.commit()
    print("Weekly plan tables cleared.")

    active_plan = SeasonalPlannerService.get_active_plan(user_id)

    if active_plan is None:
        print(f"WARNING: No active seasonal plan found for user {user_id} — skipping entry updates.")
    else:
        entries = active_plan.entries
        for i, update_dict in enumerate(ENTRY_UPDATES):
            if i >= len(entries):
                print(f"WARNING: ENTRY_UPDATES[{i}] has no matching entry in the plan — skipping.")
                continue

            if entries[i].feasibility == "Not Feasible":
                print(f"  Entry {i} ({entries[i].id}): Not Feasible — skipping (no dates for infeasible crops).")
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
