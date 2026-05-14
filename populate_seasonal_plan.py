"""Seed 15 seasonal plans that demonstrate every adjustment outcome:

  Outcome A – No adjustment        : ideal soil (≥0.7) + ideal water (≥0.7)
  Outcome B – Irrigation +4        : Maize+Sandy soil  (score 0.5 → significant increase days)
  Outcome C – Irrigation +2        : Cotton+Sandy soil (score 0.5 → minimal increase days)
  Outcome D – Sowing/harvest delay : Sandy soil actions include a sowing delay that
                                     cascades to harvesting, irrigation start & fertilization date
  Outcome E – Irrigation -4        : Maize+Recycled or Cotton+Recycled water (significant decrease days)
  Outcome F – Irrigation -2        : Cotton+River water (score 0.65 → minimal decrease days)
  Outcome G – All dates nullified   : Not-Feasible soil or water → avoid action

  user_id=1 is guaranteed 3 plans: exactly 1 active, 2 inactive (as required).

  Combined outcomes (soil then water applied in sequence):
  ┌────┬────────┬───────┬─────────────┬────────┬─────────────────────────────────────────────┐
  │  # │ user   │ crop  │ soil        │ water  │ Expected adjustments                        │
  ├────┼────────┼───────┼─────────────┼────────┼─────────────────────────────────────────────┤
  │  1 │ 1 ✅  │ Maize │ Loamy       │ GW     │ A – none                                    │
  │  2 │ 1 ❌  │ Maize │ Sandy       │ GW     │ B+D – irr+4, sowing/harvest delay +4d, fert │
  │  3 │ 1 ❌  │ Rice  │ Clay        │ Recyld │ G – water avoid → all dates null             │
  │  4 │ 2 ✅  │ Rice  │ Clay        │ River  │ A – none                                    │
  │  5 │ 2 ❌  │ Ctttn │ Sandy       │ GW     │ C+D – irr+2, sowing/harvest delay +4d, fert │
  │  6 │ 2 ❌  │ Ctttn │ Loamy       │ River  │ F – irr-2 (water)                           │
  │  7 │ 3 ✅  │ Ctttn │ Loamy       │ GW     │ A – none                                    │
  │  8 │ 3 ❌  │ Maize │ Sandy       │ Recyld │ B+D+E – irr+4, sowing delay +4d, irr-4 net=0│
  │  9 │ 4 ✅  │ Rice  │ Loamy       │ GW     │ A – none                                    │
  │ 10 │ 4 ❌  │ Maize │ Clay        │ River  │ G – soil avoid → all dates null              │
  │ 11 │ 5 ✅  │ Ctttn │ Sandy       │ River  │ C+D+F – irr+2, sowing delay +4d, irr-2 net=0│
  │ 12 │ 5 ❌  │ Rice  │ Sandy       │ GW     │ G – soil avoid → all dates null              │
  │ 13 │ 6 ✅  │ Ctttn │ Sandy       │ Recyld │ C+D+E – irr+2, sowing delay +4d, irr-4      │
  │ 14 │ 6 ❌  │ Ctttn │ Loamy       │ Recyld │ E – irr-4 (water only)                      │
  │ 15 │ 7 ✅  │ Rice  │ Loamy       │ River  │ A – none                                    │
  └────┴────────┴───────┴─────────────┴────────┴─────────────────────────────────────────────┘
"""

from app.models.seasonal_plan import SeasonalPlan
from app.extensions import db
from app.services.seasonal_planner_service import SeasonalPlannerService
from app.repositories.seasonal_plan_repository import SeasonalPlanRepository


# ── Plan definitions ───────────────────────────────────────────────────────────
# (user_id, crop, soil_type, water_source, growth_stage, currently_active)
PLANS = [
    # ── user 1: 1 active, 2 inactive (required) ───────────────────────────────
    (1, "Maize",  "Loamy", "Groundwater", "Seedling", True),   #  1 – A: no adjustment
    (1, "Maize",  "Sandy", "Groundwater", "Seedling", False),  #  2 – B+D: irr +4 (sig), sowing/harvest delay +4 d, fert note
    (1, "Rice",   "Clay",  "Recycled",    "Seedling", False),  #  3 – G: water avoid → all dates null

    # ── user 2 ────────────────────────────────────────────────────────────────
    (2, "Rice",   "Clay",  "River",       "Seedling", True),   #  4 – A: no adjustment
    (2, "Cotton", "Sandy", "Groundwater", "Seedling", False),  #  5 – C+D: irr +2 (min), sowing/harvest delay +4 d, fert note
    (2, "Cotton", "Loamy", "River",       "Seedling", False),  #  6 – F: irr -2 (water minimal)

    # ── user 3 ────────────────────────────────────────────────────────────────
    (3, "Cotton", "Loamy", "Groundwater", "Seedling", True),   #  7 – A: no adjustment
    (3, "Maize",  "Sandy", "Recycled",    "Seedling", False),  #  8 – B+D+E: irr +4, sowing delay +4 d, then irr -4 → net irr=0

    # ── user 4 ────────────────────────────────────────────────────────────────
    (4, "Rice",   "Loamy", "Groundwater", "Seedling", True),   #  9 – A: no adjustment
    (4, "Maize",  "Clay",  "River",       "Seedling", False),  # 10 – G: soil avoid → all dates null

    # ── user 5 ────────────────────────────────────────────────────────────────
    (5, "Cotton", "Sandy", "River",       "Seedling", True),   # 11 – C+D+F: irr +2, sowing delay +4 d, then irr -2 → net irr=0
    (5, "Rice",   "Sandy", "Groundwater", "Seedling", False),  # 12 – G: soil avoid → all dates null

    # ── user 6 ────────────────────────────────────────────────────────────────
    (6, "Cotton", "Sandy", "Recycled",    "Seedling", True),   # 13 – C+D+E: irr +2, sowing delay +4 d, then irr -4 → net irr=-2
    (6, "Cotton", "Loamy", "Recycled",    "Seedling", False),  # 14 – E: irr -4 (water significant only)

    # ── user 7 ────────────────────────────────────────────────────────────────
    (7, "Rice",   "Loamy", "River",       "Seedling", True),   # 15 – A: no adjustment
]


# ── Seeder ─────────────────────────────────────────────────────────────────────
class SeasonalPlanSeeder:

    def seed_all(self):
        self._clear_tables()
        for user_id, crop, soil_type, water_source, growth_stage, active in PLANS:
            # generate_initial_plan runs the rule engine, applies all adjustments,
            # persists the plan with currently_active=True, and returns the saved model
            plan = SeasonalPlannerService.generate_initial_plan(
                user_id, crop, soil_type, water_source, growth_stage
            )
            if not active:
                SeasonalPlanRepository.update(plan, {"currently_active": False})

    def _clear_tables(self):
        SeasonalPlan.query.delete()
        db.session.commit()


def run():
    SeasonalPlanSeeder().seed_all()
