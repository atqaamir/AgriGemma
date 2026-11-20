"""Demo weather scenarios for the Weather Change Simulator.

Starting state (fresh start / Reset demo): the forecast equals the baseline weather – calm,
hot and dry early May – so the plan is as planned. A scenario writes the full 7-day forecast
for the user's region (baseline + the scenario's days) and the simulator then runs the
complete daily update. Every change in the plan, tasks and notifications comes from the
rules. Scenarios 1 and 2 change only the forecast. Scenario 3 ("Sowing window running out")
also changes the plan: cotton's planned sowing date becomes 24 April (not sown), so its
sowing window (24 Apr–8 May) ends inside the forecast; it also removes the seeded "Sowing
week ahead" note, which would no longer be true. Any other scenario first restores both.

The active scenario is kept in memory per user (1 gunicorn worker). A restart reseeds the
data, so "no scenario" and the calm forecast always go together.
"""
from datetime import datetime, timedelta

from app.extensions import db
from app.utils import clock

TYPICAL = "typical"
HEAVY_RAIN = "heavy_rain"
WINDOW_RUNNING_OUT = "window_running_out"
DEFAULT = TYPICAL

# Day offset from today → (avg temp °C, humidity %, rainfall mm, sunlight h, wind km/h, notes)
SCENARIOS = {
    TYPICAL: {
        "label": "Light showers (normal for May)",
        "full_name": "Expected change: typical early-May weather",
        "banner": None,
        "days": {
            # Early-May western disturbance (common in Punjab): dust storm, then light showers.
            2: (27.5, 58, 8.0, 5.5, 38, "Western disturbance: dust storm, then thundershowers."),
            3: (28.0, 55, 4.0, 6.0, 24, "Unsettled; scattered showers and cloud."),
        },
        "info": ("A western disturbance brings light showers (8 mm and 4 mm), cloud and 27–28 °C on 7–8 May "
                 "– common in early May. Result from the rules: cotton sowing moves "
                 "from 7 to 9 May (temperature 20–30 °C and sunlight 4–8 h on 7–8 May); harvest, irrigation start "
                 "and fertilization move with it. Maize stays on 6 May."),
    },
    HEAVY_RAIN: {
        "label": "Heavy rain (unusual for May)",
        "full_name": "Unexpected change: heavy rain, unusual for early May",
        "banner": "Simulated scenario: heavy rain (unusual for May)",
        "days": {
            # Thunderstorms: heavy rain, very humid, little sun, a few degrees cooler.
            1: (27.0, 86, 38.0, 2.5, 22, "Thunderstorms; heavy rain."),
            2: (25.5, 92, 62.0, 1.5, 28, "Severe thunderstorms; very heavy rain."),
            3: (26.5, 89, 45.0, 3.0, 20, "Thunderstorms continuing; heavy rain."),
        },
        "info": ("Thunderstorms with 38, 62 and 45 mm of rain on 6–8 May – far above the app's normal for May "
                 "(8 mm for the whole month). Result from the rules: waterlogged seed beds (soil moisture >60 % "
                 "after ≥20 mm rain), so maize sowing moves from 6 to 10 May and cotton from 7 to 10 May; "
                 "harvest, irrigation start and fertilization move with them, and the Sow Maize task moves to 10 May."),
    },
    WINDOW_RUNNING_OUT: {
        "label": "Sowing window running out",
        "full_name": "Simulated plan change + forecast: cotton's sowing window running out",
        "banner": "Simulated scenario: cotton planned for 24 April, not sown – sowing window running out",
        # Plan change (simulated): this crop's planned sowing date = today + offset (5 May - 11 = 24 Apr);
        # irrigation start, fertilization and harvest move with it (seasonal plan cascade).
        "plan": {"crop": "Cotton", "sowing_offset_days": -11},
        "remove_seed_notes": ["Sowing week ahead"],
        "days": {
            # A slow western disturbance: cloud, a few showers and 27-28.5 °C on 5-8 May.
            0: (28.0, 62, 3.0, 5.0, 30, "Western disturbance: cloud and a few showers."),
            1: (27.0, 66, 6.0, 4.5, 26, "Cloudy with showers."),
            2: (27.5, 64, 5.0, 5.5, 24, "Cloudy; scattered showers."),
            3: (28.5, 58, 2.0, 6.5, 20, "Clearing slowly."),
        },
        "info": ("Not only the forecast: this scenario also changes the plan – cotton's planned sowing date "
                 "becomes 24 April (not sown), so its sowing window is 24 April–8 May. The forecast: a slow "
                 "western disturbance with cloud, a few showers (2–6 mm), 27–28.5 °C and 4.5–6.5 h of sun on "
                 "5–8 May – within the usual range for May; hot and sunny again from 9 May. Result from the "
                 "rules: no day left in cotton's window is suitable (temperature 20–30 °C, sunlight 4–8 h), so "
                 "the plan asks for a decision – a “Decide: Cotton sowing” task with an AI recommendation; the "
                 "decision is the farmer's. Maize stays on 6 May. Another scenario or Reset demo puts cotton "
                 "back on 7 May."),
    },
}

# Plan changes made by a scenario (restored before any other scenario runs; Reset reseeds).
_plan_changes = {}   # user_id -> [(seasonal entry id, original sowing "MM/DD/YYYY")]
_removed_notes = {}  # user_id -> [dict of a removed seeded notification]

_active = {}   # user_id -> scenario key


def options() -> list:
    """Dropdown entries: short label; the info icon shows the full name + description."""
    return [{"key": k, "label": s["label"], "info": f"{s['full_name']}. {s['info']}"} for k, s in SCENARIOS.items()]


def active(user_id: int):
    return _active.get(user_id)


def banner(user_id: int):
    key = _active.get(user_id)
    return SCENARIOS[key]["banner"] if key else None


def clear(user_id: int = None) -> None:
    """Forget the active scenario (Reset demo reseeds, so the plan changes are gone too)."""
    if user_id is None:
        _active.clear()
        _plan_changes.clear()
        _removed_notes.clear()
    else:
        _active.pop(user_id, None)
        _plan_changes.pop(user_id, None)
        _removed_notes.pop(user_id, None)


def _restore_plan(user_id: int) -> None:
    """Undo a previous scenario's plan change and put back the seeded notes it removed."""
    from app.models.notification import Notification
    from app.services.seasonal_planner_service import SeasonalPlannerService
    for entry_id, sowing in _plan_changes.pop(user_id, []):
        SeasonalPlannerService.update_entry(entry_id, {"sowing": sowing})
    for note in _removed_notes.pop(user_id, []):
        db.session.add(Notification(**note))
    db.session.commit()


def _apply_plan(user_id: int, key: str) -> None:
    """Scenario 3: move the crop's planned sowing date (cascade) and remove the seeded notes."""
    from app.models.notification import Notification
    from app.models.seasonal_plan import SeasonalPlan
    from app.services.seasonal_planner_service import SeasonalPlannerService
    sc = SCENARIOS[key]
    change = sc.get("plan")
    if change:
        plan = SeasonalPlan.query.filter_by(user_id=user_id, currently_active=True).first()
        entry = next((e for e in (plan.entries if plan else [])
                      if e.crop_name_rel and e.crop_name_rel.name == change["crop"] and e.sowing), None)
        if entry is None:
            raise ValueError(f"scenario {key!r}: no {change['crop']} entry in the active seasonal plan")
        new = (clock.today() + timedelta(days=change["sowing_offset_days"])).strftime("%m/%d/%Y")
        _plan_changes.setdefault(user_id, []).append((entry.id, entry.sowing))
        SeasonalPlannerService.update_entry(entry.id, {"sowing": new})
    for title in sc.get("remove_seed_notes", []):
        for n in Notification.query.filter_by(user_id=user_id, title=title).all():
            _removed_notes.setdefault(user_id, []).append(
                {c.name: getattr(n, c.name) for c in Notification.__table__.columns if c.name != "id"})
            db.session.delete(n)
    db.session.commit()


def forecast_rows(region: str, key: str, start=None) -> list:
    """The scenario's 7-day forecast: baseline weather of the region + the scenario's days."""
    from app.models.weather import Weather
    start = start or clock.today()
    base = {w.date: w for w in Weather.query.filter(
        Weather.region == region, Weather.date >= start, Weather.date <= start + timedelta(days=6))}
    rows = []
    for off in range(7):
        day = start + timedelta(days=off)
        b = base.get(day)
        if off in SCENARIOS[key]["days"]:
            vals = SCENARIOS[key]["days"][off]
        elif b is not None:
            vals = (b.avg_temperature_c, b.humidity, b.rainfall_mm, b.sunlight_hours, b.wind_speed_kph,
                    "As expected for the season.")
        else:
            continue
        rows.append((day, vals))
    return rows


def apply(user_id: int, key: str) -> dict:
    """Write the scenario's forecast for the user's region and mark it active.
    The caller runs the daily update. Returns {"region", "days": [...]}."""
    if key not in SCENARIOS:
        raise ValueError(f"unknown scenario {key!r}")
    from app.models.weather_forecast import WeatherForecast
    from app.services.domain_service.user_service import UserService
    region = UserService.get_user_location(user_id)
    if not region:
        raise ValueError(f"user {user_id} has no location")
    rows = forecast_rows(region, key)
    if not rows:
        raise ValueError(f"no baseline weather for {region}")
    days = [d for d, _ in rows]
    WeatherForecast.query.filter(WeatherForecast.region == region,
                                 WeatherForecast.date >= min(days), WeatherForecast.date <= max(days)).delete()
    for day, (t, h, r, s, w, note) in rows:
        db.session.add(WeatherForecast(region=region, date=day, avg_temperature_c=t, humidity=h, rainfall_mm=r,
                                       sunlight_hours=s, wind_speed_kph=w, notes=note, created_at=datetime.utcnow()))
    db.session.commit()
    _restore_plan(user_id)
    _apply_plan(user_id, key)
    _active[user_id] = key
    return {"region": region, "days": [d.isoformat() for d in days]}
