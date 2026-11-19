"""Demo weather scenarios for the Weather Change Simulator.

Starting state (fresh start / Reset demo): the forecast equals the baseline weather – calm,
hot and dry early May – so the plan is as planned. A scenario writes the full 7-day forecast
for the user's region (baseline + the scenario's days) and the simulator then runs the
complete daily update. Every change in the plan, tasks and notifications comes from the
rules; nothing here touches the plan.

The active scenario is kept in memory per user (1 gunicorn worker). A restart reseeds the
data, so "no scenario" and the calm forecast always go together.
"""
from datetime import datetime, timedelta

from app.extensions import db
from app.utils import clock

TYPICAL = "typical"
HEAVY_RAIN = "heavy_rain"
DEFAULT = TYPICAL

# Day offset from today → (avg temp °C, humidity %, rainfall mm, sunlight h, wind km/h, notes)
SCENARIOS = {
    TYPICAL: {
        "label": "Typical May weather",
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
        "label": "Unusual heavy rain",
        "full_name": "Unexpected change: heavy rain, unusual for early May",
        "banner": "Simulated scenario: unusual heavy rain for early May",
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
}

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
    if user_id is None:
        _active.clear()
    else:
        _active.pop(user_id, None)


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
    _active[user_id] = key
    return {"region": region, "days": [d.isoformat() for d in days]}
