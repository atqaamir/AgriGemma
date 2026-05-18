"""
refresh_data.py

Wipes and reseeds all test data in the correct dependency order:
  1. seed_data           — clears everything; inserts users, fields, crops, tasks, weather
  2. populate_seasonal_plan — clears seasonal plans; regenerates them from scratch
  3. populate_weekly_plan   — clears weekly plans; regenerates them from the active seasonal plan
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app
import Test_Runs.seed_data as seed_data
import Test_Runs.populate_seasonal_plan as populate_seasonal_plan
import Test_Runs.populate_weekly_plan as populate_weekly_plan

app = create_app()

with app.app_context():
    print("=" * 52)
    print("  Step 1/3 — Seeding base data")
    print("=" * 52)
    seed_data.run()

    print()
    print("=" * 52)
    print("  Step 2/3 — Populating seasonal plans")
    print("=" * 52)
    populate_seasonal_plan.run()

    print()
    print("=" * 52)
    print("  Step 3/3 — Populating weekly plan")
    print("=" * 52)
    populate_weekly_plan.run()

    print()
    print("=" * 52)
    print("  All data refreshed successfully.")
    print("=" * 52)
