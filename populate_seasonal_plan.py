"""Seed seasonal plans that demonstrate every adjustment outcome across
multi-crop plans (1, 2, and 3 crops per plan).

Adjustment outcomes per crop entry
  A - No adjustment          : ideal soil (>=0.7) + ideal water (>=0.7)
  B - Irrigation +4          : Maize+Sandy soil  (significant increase days)
  C - Irrigation +2          : Cotton+Sandy soil (minimal increase days)
  D - Sowing/harvest delay   : Sandy soil -> sowing delay cascades to harvesting,
                               irrigation start, and fertilization date
  E - Irrigation -4          : Maize+Recycled or Cotton+Recycled water (significant decrease)
  F - Irrigation -2          : Cotton+River water (minimal decrease)
  G - All dates nullified    : avoid action (incompatible soil or water)

Plan layout  (user_id=1 has exactly 1 active plan and 2 inactive plans)

  Plan  user  active  crops (crop / soil / water)                   Expected outcomes per crop
  ----  ----  ------  ------------------------------------------   ----------------------------
   1     1     yes    Maize  / Loamy / Groundwater                  A
                      Cotton / Loamy / Groundwater                  A
                      Rice   / Clay  / River                        A
   2     1     no     Maize  / Sandy / Groundwater                  B + D
                      Cotton / Sandy / Groundwater                  C + D
   3     1     no     Rice   / Clay  / Recycled                     G (water avoid)
   4     2     yes    Rice   / Loamy / Groundwater                  A
                      Cotton / Sandy / River                        C + D + F
   5     2     no     Maize  / Sandy / Recycled                     B + D + E
   6     3     yes    Cotton / Loamy / Groundwater                  A
                      Maize  / Clay  / River                        G (soil avoid)
                      Rice   / Loamy / River                        A
   7     3     no     Cotton / Sandy / Recycled                     C + D + E
                      Cotton / Loamy / Recycled                     E
   8     4     yes    Maize  / Loamy / Groundwater                  A
   9     4     no     Rice   / Sandy / Groundwater                  G (soil avoid)
                      Cotton / Loamy / River                        F
  10     5     yes    Rice   / Clay  / River                        A
                      Cotton / Sandy / River                        C + D + F
                      Maize  / Sandy / Groundwater                  B + D
"""

from app.models.seasonal_plan import SeasonalPlan, SeasonalPlanEntry
from app.extensions import db
from app.services.seasonal_planner_service import SeasonalPlannerService
from app.repositories.seasonal_plan_repository import SeasonalPlanRepository


# ── Plan definitions ───────────────────────────────────────────────────────────
# Each tuple: (user_id, growth_stage, currently_active, [crop dicts])
PLANS = [
    # ── user 1: 1 active (3 crops), 2 inactive ────────────────────────────────
    (1, "Sowing", True, [
        {"crop": "Maize",  "soil_type": "Loamy", "water_source": "Groundwater"},  # A
        {"crop": "Cotton", "soil_type": "Loamy", "water_source": "Groundwater"},  # A
        {"crop": "Rice",   "soil_type": "Clay",  "water_source": "River"},        # A
    ]),
    (1, "Sowing", False, [
        {"crop": "Maize",  "soil_type": "Sandy", "water_source": "Groundwater"},  # B+D
        {"crop": "Cotton", "soil_type": "Sandy", "water_source": "Groundwater"},  # C+D
    ]),
    (1, "Sowing", False, [
        {"crop": "Rice",   "soil_type": "Clay",  "water_source": "Recycled"},     # G (water avoid)
    ]),

    # ── user 2 ────────────────────────────────────────────────────────────────
    (2, "Sowing", True, [
        {"crop": "Rice",   "soil_type": "Loamy", "water_source": "Groundwater"},  # A
        {"crop": "Cotton", "soil_type": "Sandy", "water_source": "River"},        # C+D+F
    ]),
    (2, "Sowing", False, [
        {"crop": "Maize",  "soil_type": "Sandy", "water_source": "Recycled"},     # B+D+E
    ]),

    # ── user 3 ────────────────────────────────────────────────────────────────
    (3, "Sowing", True, [
        {"crop": "Cotton", "soil_type": "Loamy", "water_source": "Groundwater"},  # A
        {"crop": "Maize",  "soil_type": "Clay",  "water_source": "River"},        # G (soil avoid)
        {"crop": "Rice",   "soil_type": "Loamy", "water_source": "River"},        # A
    ]),
    (3, "Sowing", False, [
        {"crop": "Cotton", "soil_type": "Sandy", "water_source": "Recycled"},     # C+D+E
        {"crop": "Cotton", "soil_type": "Loamy", "water_source": "Recycled"},     # E
    ]),

    # ── user 4 ────────────────────────────────────────────────────────────────
    (4, "Sowing", True, [
        {"crop": "Maize",  "soil_type": "Loamy", "water_source": "Groundwater"},  # A
    ]),
    (4, "Sowing", False, [
        {"crop": "Rice",   "soil_type": "Sandy", "water_source": "Groundwater"},  # G (soil avoid)
        {"crop": "Cotton", "soil_type": "Loamy", "water_source": "River"},        # F
    ]),

    # ── user 5 ────────────────────────────────────────────────────────────────
    (5, "Sowing", True, [
        {"crop": "Rice",   "soil_type": "Clay",  "water_source": "River"},        # A
        {"crop": "Cotton", "soil_type": "Sandy", "water_source": "River"},        # C+D+F
        {"crop": "Maize",  "soil_type": "Sandy", "water_source": "Groundwater"},  # B+D
    ]),
]


# ── Seeder ─────────────────────────────────────────────────────────────────────
class SeasonalPlanSeeder:

    def seed_all(self):
        self._clear_tables()
        for user_id, growth_stage, active, crops in PLANS:
            plan = SeasonalPlannerService.generate_plan(user_id, growth_stage, crops)
            if not active:
                SeasonalPlanRepository.update(plan, {"currently_active": False})

    def _clear_tables(self):
        SeasonalPlanEntry.query.delete()
        SeasonalPlan.query.delete()
        db.session.commit()


def run():
    SeasonalPlanSeeder().seed_all()
