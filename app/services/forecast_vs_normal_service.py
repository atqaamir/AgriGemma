"""Forecast vs. the app's climate normal for the month (no AI) – chatbot grounding.

When the forecast differs from the baseline weather (a forecast change), the chatbot gets
a short block: the changed forecast days, the 7-day forecast against the app's normal for
the month (region climate profile), a verdict (typical for the season / unusual), the plan
events and tasks that changed today, and the rule reasons behind the sowing moves.

Verdict (placeholder thresholds, ASSUMPTIONS.md): unusual when the 7-day forecast rain is
more than UNUSUAL_RAIN_FACTOR × the month's normal rain and at least UNUSUAL_RAIN_MIN_MM,
or the average forecast temperature is UNUSUAL_TEMP_DELTA_C or more away from the month's
normal mean ((max + min) / 2). Otherwise typical for the season.
"""
import json
from datetime import timedelta

from app.utils import clock

UNUSUAL_RAIN_FACTOR = 2.0
UNUSUAL_RAIN_MIN_MM = 20.0
UNUSUAL_TEMP_DELTA_C = 7.0
_FIELDS = (("avg_temperature_c", "°C"), ("rainfall_mm", "mm"), ("sunlight_hours", "h sun"), ("humidity", "% humidity"))


def _fmt(d):
    return f"{d.day} {d.strftime('%b')}"


def _num(v):
    return f"{v:g}" if isinstance(v, (int, float)) else "?"


def _day_values(row) -> str:
    return ", ".join(f"{_num(getattr(row, a))} {u}" for a, u in _FIELDS)


def _changed(base, fc) -> bool:
    return any(abs((getattr(base, a) or 0) - (getattr(fc, a) or 0)) > 0.05 for a, _ in _FIELDS)


def build(user_id: int, today=None) -> dict | None:
    """The comparison for the user's region, or None without a forecast change."""
    from app.models.weather import Weather
    from app.models.weather_forecast import WeatherForecast
    from app.services.domain_service.user_service import UserService
    from app.services.weather_service.weather_fetch_api import get_monthly_climate

    today = today or clock.today()
    region = UserService.get_user_location(user_id)
    if not region:
        return None
    end = today + timedelta(days=6)
    base = {w.date: w for w in Weather.query.filter(Weather.region == region, Weather.date >= today,
                                                   Weather.date <= end)}
    fcs = sorted(WeatherForecast.query.filter(WeatherForecast.region == region, WeatherForecast.date >= today,
                                              WeatherForecast.date <= end), key=lambda r: r.date)
    changed = [(f, base[f.date]) for f in fcs if f.date in base and _changed(base[f.date], f)]
    if not fcs or not changed:
        return None

    normal = get_monthly_climate(region, today.month)
    normal_mean = (normal["avg_max_temp_c"] + normal["avg_min_temp_c"]) / 2
    week_rain = round(sum(f.rainfall_mm or 0 for f in fcs), 1)
    rain_days = sum(1 for f in fcs if (f.rainfall_mm or 0) >= 1)
    temps = [f.avg_temperature_c for f in fcs if f.avg_temperature_c is not None]
    week_temp = round(sum(temps) / len(temps), 1) if temps else None

    reasons = []
    if week_rain >= UNUSUAL_RAIN_MIN_MM and week_rain > UNUSUAL_RAIN_FACTOR * normal["avg_rainfall_mm"]:
        reasons.append(f"{week_rain:g} mm of rain in 7 days against {normal['avg_rainfall_mm']:g} mm for the whole "
                       f"month of {normal['name']}")
    if week_temp is not None and abs(week_temp - normal_mean) >= UNUSUAL_TEMP_DELTA_C:
        reasons.append(f"average {week_temp:g} °C against a normal mean of {normal_mean:g} °C")

    return {
        "region": region,
        "month": normal["name"],
        "verdict": "unusual" if reasons else "typical",
        "unusual_because": reasons,
        "normal": {"max_c": normal["avg_max_temp_c"], "min_c": normal["avg_min_temp_c"], "mean_c": normal_mean,
                   "rain_mm": normal["avg_rainfall_mm"], "rain_days": normal["avg_rain_days"],
                   "condition": normal["condition"]},
        "forecast": {"rain_mm": week_rain, "rain_days": rain_days, "avg_temp_c": week_temp,
                     "first": fcs[0].date.isoformat(), "last": fcs[-1].date.isoformat()},
        "changed_days": [{"date": f.date.isoformat(), "forecast": _day_values(f), "baseline": _day_values(b),
                          "notes": f.notes} for f, b in changed],
        "plan_changes": _plan_changes(user_id, today),
        "task_changes": _task_changes(user_id, today),
    }


def _plan_changes(user_id: int, today) -> list:
    """Today's forecast shifts (event, from → to) and, for sowing, the rules that made the
    skipped days unsuitable (factor band + the rulebook's reasoning text)."""
    from app.models.plan_event_override import PlanEventOverride
    from app.models.seasonal_plan import SeasonalPlan
    from app.rules.rule_engine.rule_engine import RuleEngine
    from app.services.plan_override_service import PlanOverrideService

    plan = SeasonalPlan.query.filter_by(user_id=user_id, currently_active=True).first()
    if not plan:
        return []
    out = []
    for entry in plan.entries:
        crop = entry.crop_name_rel.name if entry.crop_name_rel else f"Crop {entry.crop_name_id}"
        overrides = PlanEventOverride.query.filter_by(seasonal_plan_entry_id=entry.id, source="forecast_shift",
                                                      as_of_date=today).all()
        for o in sorted(overrides, key=lambda o: ["sowing", "irrigation_start", "fertilization",
                                                  "harvesting"].index(o.event_type)
                        if o.event_type in ("sowing", "irrigation_start", "fertilization", "harvesting") else 9):
            if o.original_date == o.actual_date:
                continue
            item = {"crop": crop, "event": o.event_type.replace("_", " "),
                    "from": o.original_date.isoformat() if o.original_date else None,
                    "to": o.actual_date.isoformat(), "rules": []}
            if o.event_type == "sowing" and o.original_date:
                active = PlanOverrideService.active_crop_for_entry(entry, user_id)
                field = active.field if active else None
                item["field"] = field.name if field else None
                item["rules"] = _sowing_rules(entry, field, max(o.original_date, today), o.actual_date)
            out.append(item)
    return out


def _sowing_rules(entry, field, first, new_date) -> list:
    """Why the days before the new sowing date were unsuitable: per day the blocking
    factors (band) and, once per rule, the rulebook's reasoning text."""
    from app.rules.rule_engine.rule_engine import RuleEngine
    location = field.location if field else None
    if not location:
        return []
    lookup = RuleEngine.get_forecast_by_region_and_date
    stage = entry.growth_id or 4
    lookups = {f: fn for f, _, fn, _ in RuleEngine._rule_factors()}
    rules, seen = [], {}
    day = first
    while day < new_date:
        wet = RuleEngine._seedbed_wet(location, day, lookup)
        res = RuleEngine._assess_sowing_day(entry.crop_name_id, stage, lookup(location, day),
                                            field.moisture_level, field.ph_level, seedbed_wet=wet)
        if res:
            blocking, bands = res
            for f in blocking:
                key = (f, bands[f])
                label = RuleEngine._band_text(f, bands[f]) + (RuleEngine.SEEDBED_WET_NOTE if wet and f == "soil_moisture"
                                                             else "")
                if key not in seen:
                    rule = lookups[f](entry.crop_name_id, stage, bands[f])
                    seen[key] = {"rule": label, "reasoning": getattr(rule, "reasoning", "") or "", "days": []}
                    rules.append(seen[key])
                seen[key]["days"].append(_fmt(day))
        day += timedelta(days=1)
    return rules


def _task_changes(user_id: int, today) -> list:
    from app.models.task import Task
    out = []
    for t in Task.query.filter_by(user_id=user_id, changed_on=today).all():
        try:
            history = json.loads(t.task_changes or "[]")
        except (TypeError, ValueError):
            continue
        for ch in (history if isinstance(history, list) else [history]):
            if ch.get("changed_on") != today.isoformat():
                continue
            ct, ov, nv = ch.get("change_type"), ch.get("original_value"), ch.get("new_value")
            if ct == "due_date":
                out.append(f"{t.title}: moved from {ov} to {nv}")
            elif ct == "is_active":
                out.append(f"{t.title}: {'cancelled' if not nv else 'back on the list'}")
    return out


def block(data: dict | None) -> str:
    """Compact prompt block, or "" without a forecast change."""
    if not data:
        return ""
    from datetime import date
    d = lambda iso: _fmt(date.fromisoformat(iso))
    n, f = data["normal"], data["forecast"]
    title = "UNUSUAL WEATHER" if data["verdict"] == "unusual" else "FORECAST CHANGE (TYPICAL FOR THE SEASON)"
    lines = [f"[{title}] {data['region']}, forecast {d(f['first'])}–{d(f['last'])}"]
    for c in data["changed_days"]:
        lines.append(f"- {d(c['date'])}: {c['forecast']} (expected before: {c['baseline']})")
    lines.append(f"- 7-day forecast: {f['rain_mm']:g} mm rain on {f['rain_days']} day(s), average {_num(f['avg_temp_c'])} °C.")
    lines.append(f"- The app's normal for {data['month']}: max {n['max_c']:g} °C, min {n['min_c']:g} °C, "
                 f"{n['rain_mm']:g} mm rain on {n['rain_days']:g} days for the whole month ({n['condition']}).")
    if data["verdict"] == "unusual":
        lines.append("- Verdict: UNUSUAL compared to the app's normal for " + data["month"] + ": "
                     + "; ".join(data["unusual_because"]) + ".")
    else:
        lines.append(f"- Verdict: typical for the season – the forecast is close to the app's normal for "
                     f"{data['month']}.")
    by_crop = {}
    for p in data["plan_changes"]:
        by_crop.setdefault(p["crop"], []).append(p)
    for crop, items in by_crop.items():
        field = next((p["field"] for p in items if p.get("field")), None)
        moves = ", ".join(f"{p['event']} {d(p['from']) if p['from'] else '?'} → {d(p['to'])}" for p in items)
        lines.append(f"- Plan change, {crop}{f' ({field})' if field else ''}: {moves}")
        for p in items:
            for r in p["rules"]:
                lines.append(f"  Rule on {', '.join(r['days'])}: {r['rule']} – {r['reasoning']}")
    for t in data["task_changes"]:
        lines.append(f"- Task: {t}")
    return "\n".join(lines)
