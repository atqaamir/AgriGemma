"""Every month maps to exactly one season; the season lookup and the climate context work
for all 12 months. Run from the project root: python Test_Runs/test_season_months.py
"""
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
logging.disable(logging.CRITICAL)

from app.rules.vocabulary.mappings import SEASON_MONTHS, get_vocabulary  # noqa: E402


def months_of(rng):
    start, end = rng["start"], rng["end"]
    return set(range(start, end + 1)) if start <= end else set(range(start, 13)) | set(range(1, end + 1))


names = get_vocabulary()["Season"]
owners = {m: [names[s] for s, rng in SEASON_MONTHS.items() if m in months_of(rng)] for m in range(1, 13)}
bad = {m: o for m, o in owners.items() if len(o) != 1}
for m in range(1, 13):
    print(f"  month {m:2}: {', '.join(owners[m]) or '—'}")
assert not bad, f"months without exactly one season: {bad}"
print("OK: every month maps to exactly one season")

# _current_season_id agrees with SEASON_MONTHS for every month
from app.services.rules_context_service import _current_season_id  # noqa: E402
for m in range(1, 13):
    assert names[_current_season_id(m)] == owners[m][0], (m, _current_season_id(m), owners[m])
print("OK: _current_season_id matches for all 12 months")

# climate context (current + next two months) works for every month of the demo clock
from app import create_app  # noqa: E402
from app.services.weather_service.forecast_service import ForecastService  # noqa: E402
app = create_app()
with app.app_context():
    for m in range(1, 13):
        os.environ["DEMO_TODAY"] = f"2027-{m:02d}-15"
        ctx = ForecastService.get_climate_context(1)
        assert ctx and ctx.get("current_month"), (m, ctx)
print("OK: climate context for all 12 months")
