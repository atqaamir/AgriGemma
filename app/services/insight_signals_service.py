"""Evidence-backed signals from the farm's own data — no AI.

The task insights (tasks page) and the farm report (dashboard) give the model ONLY these
signals, and every AI insight must cite signal ids; the validator drops insights whose
evidence ids or dates are not in the signals (see `app.utils.date_guard`).

Two layers:
  collect(user_id, today) → a plain snapshot (tasks, plan events, entries, forecast, fields)
  build_from(snapshot)    → signals (pure: tests can feed a made-up snapshot)

Each signal: {"id": "S1", "key": stable key (diff between reports), "kind", "severity" (1 =
most urgent), "text": one or two plain sentences with every date written out, "dates":
ISO dates in the text, "sources": {"tasks": [ids], "plan_events": [...], "forecast_days":
[ISO], "fields": [ids]}, "labels": short evidence labels for the UI ("Sow Cotton 9 May",
"showers 7–8 May")}.

Thresholds are the ones the app already uses: rain ≥ 2 mm = "Showers" and an average of
≥ 36 °C = heat (ForecastService); a dry week only when the weekly plan's rainfall rule says
so. No new agronomic numbers.
"""
from __future__ import annotations

import json
import logging
from datetime import date, timedelta

from app.utils import clock
from app.utils.date_guard import dates_in

logger = logging.getLogger(__name__)

HORIZON_DAYS = 6            # today .. today+6, the weekly plan's window
DEADLINE_DAYS = 2           # an event within 1–2 days is a deadline
RAIN_MM = 2.0               # ForecastService: rain ≥ 2 mm → "Showers"
HEAT_C = 36.0               # ForecastService: heatwave_risk at an average ≥ 36 °C
URGENT = ("critical", "high")
# Field work that rain stops (soil too wet to work, seed and soil washed away).
SOIL_WORK_TYPES = {"land_preparation", "plowing", "soil_conservation", "soil_testing", "drainage",
                   "weeding", "fertilizing", "fertilization", "planting"}
EVENT_VERB = {"sowing": "Sow", "irrigation": "Irrigate", "fertilization": "Fertilize", "harvesting": "Harvest"}
EVENT_NOUN = {"sowing": "sowing", "irrigation_start": "irrigation start", "irrigation": "irrigation",
              "fertilization": "fertilization", "harvesting": "harvest"}
KIND_ORDER = ("deadline", "dependency", "weather", "plan_change", "load", "field_status")


# ── Formatting ─────────────────────────────────────────────────────────────────

def fmt(d: date | None) -> str:
    return f"{d.day} {d.strftime('%b')}" if d else "?"


def rel(d: date, today: date) -> str:
    n = (d - today).days
    return {0: "today", 1: "tomorrow", -1: "yesterday"}.get(n, f"in {n} days" if n > 0 else f"{-n} days ago")


def day_range(days: list[date]) -> str:
    """'7–8 May' for consecutive days in one month, else '7 May, 9 May'."""
    days = sorted(days)
    if len(days) > 1 and all((b - a).days == 1 for a, b in zip(days, days[1:])) \
            and days[0].month == days[-1].month:
        return f"{days[0].day}–{days[-1].day} {days[-1].strftime('%b')}"
    return ", ".join(fmt(d) for d in days)


def _task_ref(t: dict, today: date) -> str:
    due = f"due {rel(t['due'], today)} {fmt(t['due'])}" if t["due"] else "no due date"
    return f"{t['title']} ({t['priority']}, {due})"


def _task_label(t: dict) -> str:
    return f"{t['title']} {fmt(t['due'])}" if t["due"] else t["title"]


def _event_label(e: dict) -> str:
    return f"{EVENT_VERB.get(e['event'], e['event'].title())} {e['crop']} {fmt(e['date'])}"


# ── Collect (DB → snapshot) ────────────────────────────────────────────────────

def collect(user_id: int, today: date | None = None) -> dict:
    """The user's data the signals are built from, as plain dicts."""
    from app.models.seasonal_plan import SeasonalPlan
    from app.models.weather_forecast import WeatherForecast
    from app.repositories.task_repository import TaskRepository
    from app.repositories.plan_event_override_repository import PlanEventOverrideRepository
    from app.repositories.field_repository import FieldRepository
    from app.services.domain_service.user_service import UserService
    from app.services.plan_override_service import PlanOverrideService, SEASONAL_COLUMNS, _parse
    from app.services.weekly_planning_service.weekly_planner_service import WeeklyPlannerService
    from app.services.intelligence_service.context.context_builder import _crop_status

    today = today or clock.today()
    end = today + timedelta(days=HORIZON_DAYS)

    tasks = [{
        "id": t.id, "title": t.title, "priority": t.priority or "medium", "due": t.due_date,
        "type": t.task_type, "category": t.task_category,
        "field_id": t.field_id, "field": t.field.name if t.field else None,
        "crop": t.crop.name if t.crop else None, "entry_id": t.seasonal_plan_entry_id,
    } for t in TaskRepository.get_pending(user_id)]

    # Seasonal entries → crop, field (via the active crop), feasibility, moved dates.
    entries, by_crop_name = [], {}
    plan = SeasonalPlan.query.filter_by(user_id=user_id, currently_active=True).first()
    for entry in (plan.entries if plan else []):
        name = entry.crop_name_rel.name if entry.crop_name_rel else f"Crop {entry.crop_name_id}"
        crop = PlanOverrideService.active_crop_for_entry(entry, user_id)
        field = crop.field if crop and crop.field else None
        e = {"entry_id": entry.id, "crop": name, "crop_name_id": entry.crop_name_id,
             "field_id": field.id if field else None, "field": field.name if field else None,
             "feasibility": entry.feasibility, "not_feasible_reason": None,
             "sowing_status": None, "sowing_note": None, "dry_note": None,
             "moved": [], "sowing_done_on": None}
        if entry.feasibility == "Not Feasible":
            try:
                e["not_feasible_reason"] = "; ".join(json.loads(entry.adjustments_to_make or "[]"))
            except (TypeError, ValueError):
                e["not_feasible_reason"] = entry.adjustments_to_make
        else:
            # today + 1: today's forecast decisions count too (as-of rule, same as the chatbot)
            eff = PlanOverrideService.effective_dates(entry, today + timedelta(days=1))
            e["sowing_done_on"] = eff["sowing_done_on"]
            reasons = {}
            for o in PlanEventOverrideRepository.get_applicable(entry.id, today + timedelta(days=1)):
                reasons[o.event_type] = (o.source, o.reason)
            for etype, col in SEASONAL_COLUMNS.items():
                planned, actual = _parse(getattr(entry, col)), eff.get(etype)
                if planned and actual and planned != actual:
                    source, reason = reasons.get(etype, (None, None))
                    e["moved"].append({"event": etype, "from": planned, "to": actual,
                                       "source": source, "reason": reason})
        entries.append(e)
        by_crop_name[entry.crop_name_id] = e

    # Weekly plan: events in the window, sowing status / note, dry-week rule text.
    events = []
    try:
        weekly = WeeklyPlannerService.show_active_plan(user_id).get("entries", [])
    except Exception as exc:
        logger.warning("Signals: weekly plan unavailable for user %s — %s", user_id, exc)
        weekly = []
    for w in weekly:
        e = by_crop_name.get(w.get("crop_id"))
        if e is None:
            continue
        e["sowing_status"] = w.get("sowing_status")
        for a in w.get("climate_adjustments_made") or []:
            text = a.get("adjustment") or ""
            if a.get("factor") == "sowing_window":
                e["sowing_note"] = text
            elif a.get("factor") == "rainfall" and text.lower().startswith("dry week"):
                note = text.split(";")[0].replace("[Monitor]", "").strip()
                e["dry_note"] = note[len("dry week"):].lstrip(" :–-")    # "Dry week: no extra …" → "no extra …"
        for ev in w.get("week_events") or []:
            d = date.fromisoformat(ev["date"])
            if today <= d <= end:
                events.append({"entry_id": e["entry_id"], "crop": e["crop"], "field_id": e["field_id"],
                               "field": e["field"], "event": ev["event_type"], "date": d,
                               "extra": bool(ev.get("extra")), "reason": ev.get("reason")})
    events.sort(key=lambda x: (x["date"], x["crop"]))

    region = UserService.get_user_location(user_id)
    forecast = [{
        "date": r.date, "temp": r.avg_temperature_c, "rain": r.rainfall_mm or 0.0,
        "sun": r.sunlight_hours, "humidity": r.humidity,
    } for r in (WeatherForecast.query
                .filter(WeatherForecast.region == region, WeatherForecast.date >= today,
                        WeatherForecast.date <= end)
                .order_by(WeatherForecast.date).all())]

    fields = []
    for f in FieldRepository.get_by_user_id(user_id):
        if not f.currently_active:
            continue
        crops = [c for c in f.crops if c.currently_active]
        fields.append({
            "id": f.id, "name": f.name, "health": f.health_status,
            "moisture": f.moisture_level, "stress": f.stress_risk, "disease": f.disease_risk,
            "crop_status": "; ".join(_crop_status(c) for c in crops) or "no crop",
            "bare": all(not c.planting_date for c in crops),
        })

    return {"today": today, "tasks": tasks, "events": events, "entries": entries,
            "forecast": forecast, "fields": fields}


# ── Build (snapshot → signals) ─────────────────────────────────────────────────

def _signal(kind, key, severity, text, today, tasks=(), plan_events=(), forecast_days=(), fields=(),
            labels=()) -> dict:
    year = today.year
    dates = sorted({date(year, m, d).isoformat() for d, m in dates_in(text)
                    if not (m == 2 and d == 29)})
    return {
        "kind": kind, "key": key, "severity": severity, "text": text, "dates": dates,
        "sources": {
            "tasks": sorted({t["id"] for t in tasks}),
            "plan_events": [{"crop": e["crop"], "event": e["event"], "date": e["date"].isoformat(),
                             "field": e["field"]} for e in plan_events],
            "forecast_days": sorted({d.isoformat() for d in forecast_days}),
            "fields": sorted({f for f in fields if f is not None}),
        },
        "labels": list(dict.fromkeys(labels)),
    }


def _deadlines(s: dict) -> list:
    """A one-time plan event in 1–2 days + the pending tasks on that field due before or on it."""
    today, out = s["today"], []
    for e in s["events"]:
        n = (e["date"] - today).days
        if e["event"] == "irrigation" or not 1 <= n <= DEADLINE_DAYS:
            continue
        prep = [t for t in s["tasks"]
                if t["field_id"] and t["field_id"] == e["field_id"] and t["category"] != "plan"
                and t["due"] and t["due"] <= e["date"]]
        where = f" on {e['field']}" if e["field"] else ""
        verb = EVENT_VERB.get(e["event"], e["event"].title())
        text = f"{verb} {e['crop']}{where} is {rel(e['date'], today)} ({fmt(e['date'])})."
        if prep:
            text += " Tasks on this field due before it: " + "; ".join(_task_ref(t, today) for t in prep) + "."
        else:
            text += " No preparation task is open on this field."
        own = [t for t in s["tasks"] if t["category"] == "plan" and t["entry_id"] == e["entry_id"]
               and t["due"] == e["date"]]
        out.append(_signal("deadline", f"deadline:{e['entry_id']}:{e['event']}:{e['date']}", 1, text, today,
                           tasks=prep + own, plan_events=[e], fields=[e["field_id"]],
                           labels=[_event_label(e)] + [_task_label(t) for t in prep]))
    return out


def _dependencies(s: dict) -> list:
    """Critical/high field tasks on a field with a sowing or irrigation start in 3–6 days."""
    today, out, first_irrigation = s["today"], [], set()
    for e in s["events"]:
        n = (e["date"] - today).days
        if e["event"] == "irrigation":
            if e["entry_id"] in first_irrigation:
                continue
            first_irrigation.add(e["entry_id"])
        elif e["event"] != "sowing":
            continue
        if not e["field_id"] or n <= DEADLINE_DAYS:
            continue            # the deadline signal covers events in 1–2 days
        urgent = [t for t in s["tasks"]
                  if t["field_id"] == e["field_id"] and t["category"] != "plan"
                  and t["priority"] in URGENT and (not t["due"] or t["due"] <= e["date"])]
        if not urgent:
            continue
        noun = "first irrigation" if e["event"] == "irrigation" else "sowing"
        text = (f"{e['crop']} {noun} on {e['field']} is planned for {fmt(e['date'])} ({rel(e['date'], today)}). "
                f"Open {'critical/high' if len(urgent) > 1 else urgent[0]['priority']} field "
                f"task{'s' if len(urgent) > 1 else ''} on {e['field']}: "
                + "; ".join(_task_ref(t, today) for t in urgent) + ".")
        severity = 1 if any(t["priority"] == "critical" for t in urgent) else 2
        out.append(_signal("dependency", f"dependency:{e['field_id']}:{e['entry_id']}:{e['event']}", severity,
                           text, today, tasks=urgent, plan_events=[e], fields=[e["field_id"]],
                           labels=[_event_label(e)] + [_task_label(t) for t in urgent]))
    return out


def _groups(days: list[date]) -> list[list[date]]:
    groups = []
    for d in sorted(days):
        if groups and (d - groups[-1][-1]).days == 1:
            groups[-1].append(d)
        else:
            groups.append([d])
    return groups


def _weather(s: dict) -> list:
    """Rain / heat days and the pending tasks and plan events they block or favour; a dry week
    when the weekly plan's rainfall rule says so."""
    today, out = s["today"], []
    fc = {f["date"]: f for f in s["forecast"]}

    rain_days = [d for d, f in fc.items() if (f["rain"] or 0) >= RAIN_MM]
    for g in _groups(rain_days):
        first, last = g[0], g[-1]
        amounts = ", ".join(f"{fc[d]['rain']:g} mm on {fmt(d)}" for d in g)
        before = [t for t in s["tasks"] if t["type"] in SOIL_WORK_TYPES and t["category"] != "plan"
                  and t["due"] and today <= t["due"] < first]
        on = [t for t in s["tasks"] if t["due"] and first <= t["due"] <= last]
        ev_on = [e for e in s["events"] if first <= e["date"] <= last]
        ev_after = [e for e in s["events"] if e["event"] == "sowing" and last < e["date"] <= last + timedelta(days=2)]
        word = "Showers" if len(g) > 1 or fc[first]["rain"] < 10 else "Rain"
        text = f"{word} forecast on {day_range(g)} ({amounts}) — soil work and sowing are not possible on wet days."
        if before:
            text += " Pending soil work due before then: " + "; ".join(_task_ref(t, today) for t in before) + "."
        if on:
            text += " Tasks due on those days: " + "; ".join(_task_ref(t, today) for t in on) + "."
        if ev_on:
            text += " Plan events on those days: " + "; ".join(_event_label(e) for e in ev_on) + "."
        if ev_after:
            text += " Next sowing after the rain: " + "; ".join(
                f"{_event_label(e)}" + (f" on {e['field']}" if e["field"] else "") for e in ev_after) + "."
        sev = 1 if (before or on or ev_on) else 3
        out.append(_signal("weather", f"weather:rain:{first}", sev, text, today,
                           tasks=before + on, plan_events=ev_on + ev_after, forecast_days=g,
                           fields=[t["field_id"] for t in before + on],
                           labels=[f"{word.lower()} {day_range(g)}"] + [_task_label(t) for t in before + on]
                           + [_event_label(e) for e in ev_on + ev_after]))

    heat_days = [d for d, f in fc.items() if (f["temp"] or 0) >= HEAT_C]
    for g in _groups(heat_days):
        first, last = g[0], g[-1]
        temps = ", ".join(f"{fc[d]['temp']:g} °C on {fmt(d)}" for d in g)
        on = [t for t in s["tasks"] if t["due"] and first <= t["due"] <= last]
        ev_on = [e for e in s["events"] if first <= e["date"] <= last]
        text = f"Heat on {day_range(g)} (daily average {temps})."
        if on:
            text += " Tasks due on those days: " + "; ".join(_task_ref(t, today) for t in on) + "."
        if ev_on:
            text += " Plan events on those days: " + "; ".join(_event_label(e) for e in ev_on) + "."
        out.append(_signal("weather", f"weather:heat:{first}", 2 if (on or ev_on) else 3, text, today,
                           tasks=on, plan_events=ev_on, forecast_days=g,
                           fields=[t["field_id"] for t in on],
                           labels=[f"heat {day_range(g)}"] + [_task_label(t) for t in on]
                           + [_event_label(e) for e in ev_on]))

    for e in s["entries"]:
        if e["dry_note"]:
            dry = [d for d, f in fc.items() if (f["rain"] or 0) == 0]
            text = f"Dry week for {e['crop']}" + (f" on {e['field']}" if e["field"] else "") \
                   + f" (weekly plan rainfall rule): {e['dry_note']}."
            out.append(_signal("weather", f"weather:dry:{e['entry_id']}", 3, text, today,
                               forecast_days=dry, fields=[e["field_id"]],
                               labels=[f"dry week ({e['crop']})"]))
    return out


def _plan_changes(s: dict) -> list:
    """Moved dates (planned → effective, with the reason and what cascaded), a sowing done,
    'decision needed' / overdue sowing, and crops that are not feasible this season."""
    today, out = s["today"], []
    for e in s["entries"]:
        where = f" on {e['field']}" if e["field"] else ""
        if e["feasibility"] == "Not Feasible":
            has_tasks = [t for t in s["tasks"] if t["entry_id"] == e["entry_id"]]
            text = (f"{e['crop']}{where} is Not Feasible this season: {e['not_feasible_reason'] or 'no reason given'}. "
                    f"No sowing, irrigation or other plan events are scheduled for it"
                    + (" and it has no tasks." if not has_tasks else "."))
            out.append(_signal("plan_change", f"plan:not_feasible:{e['entry_id']}", 3, text, today,
                               tasks=has_tasks, fields=[e["field_id"]],
                               labels=[f"{e['crop']} not feasible"]))
            continue
        if e["sowing_done_on"]:
            text = f"{e['crop']}{where} was sown on {fmt(e['sowing_done_on'])} (marked done by the farmer)."
            out.append(_signal("plan_change", f"plan:sown:{e['entry_id']}", 3, text, today,
                               fields=[e["field_id"]], labels=[f"{e['crop']} sown {fmt(e['sowing_done_on'])}"]))
        if e["sowing_status"] in ("decision_needed", "overdue"):
            state = "Sowing overdue – decision needed" if e["sowing_status"] == "overdue" else "Decision needed"
            text = f"{state} for {e['crop']}{where}: {e['sowing_note'] or 'no suitable sowing day in the window'}."
            out.append(_signal("plan_change", f"plan:{e['sowing_status']}:{e['entry_id']}", 1, text, today,
                               fields=[e["field_id"]], labels=[f"{e['crop']}: {state.lower()}"]))
        moved = [m for m in e["moved"] if m["source"] != "farmer_completed"]
        sow = next((m for m in moved if m["event"] == "sowing"), None)
        if sow:
            cascade = [m for m in moved if m["event"] != "sowing"]
            text = f"{e['crop']} sowing{where} moved from {fmt(sow['from'])} to {fmt(sow['to'])}"
            text += f": {sow['reason']}." if sow["reason"] else "."
            if cascade:
                text += " Moved with it: " + ", ".join(
                    f"{EVENT_NOUN.get(m['event'], m['event'])} {fmt(m['from'])} → {fmt(m['to'])}" for m in cascade) + "."
            ev = {"crop": e["crop"], "event": "sowing", "date": sow["to"], "field": e["field"]}
            out.append(_signal("plan_change", f"plan:moved:{e['entry_id']}:sowing:{sow['to']}", 2, text, today,
                               plan_events=[ev], fields=[e["field_id"]],
                               labels=[f"{e['crop']} sowing {fmt(sow['from'])} → {fmt(sow['to'])}"]))
        else:
            for m in moved:
                text = (f"{e['crop']} {EVENT_NOUN.get(m['event'], m['event'])}{where} moved from {fmt(m['from'])} "
                        f"to {fmt(m['to'])}" + (f": {m['reason']}." if m["reason"] else "."))
                out.append(_signal("plan_change", f"plan:moved:{e['entry_id']}:{m['event']}:{m['to']}", 3, text,
                                   today, fields=[e["field_id"]],
                                   labels=[f"{e['crop']} {EVENT_NOUN.get(m['event'], m['event'])} "
                                           f"{fmt(m['from'])} → {fmt(m['to'])}"]))
    return out


def _load(s: dict) -> list:
    """High/critical tasks per day in the window, and overdue tasks."""
    today, out = s["today"], []
    overdue = [t for t in s["tasks"] if t["due"] and t["due"] < today]
    if overdue:
        text = f"{len(overdue)} overdue task{'s' if len(overdue) > 1 else ''}: " + "; ".join(
            _task_ref(t, today) for t in overdue) + "."
        out.append(_signal("load", "load:overdue", 1, text, today, tasks=overdue,
                           fields=[t["field_id"] for t in overdue],
                           labels=[f"{len(overdue)} overdue"] + [_task_label(t) for t in overdue]))
    per_day = {}
    for t in s["tasks"]:
        if t["priority"] in URGENT and t["due"] and today <= t["due"] <= today + timedelta(days=HORIZON_DAYS):
            per_day.setdefault(t["due"], []).append(t)
    if per_day:
        parts = []
        for d in sorted(per_day):
            ts = per_day[d]
            crit = sum(1 for t in ts if t["priority"] == "critical")
            parts.append(f"{rel(d, today)} {fmt(d)}: {len(ts)} ({crit} critical)" if crit
                         else f"{rel(d, today)} {fmt(d)}: {len(ts)}")
        busiest = max(per_day, key=lambda d: (len(per_day[d]), -d.toordinal()))
        text = ("High/critical tasks per day — " + "; ".join(parts) + f". Busiest day: {fmt(busiest)} with "
                + ", ".join(f"{t['title']} ({t['priority']})" for t in per_day[busiest]) + ".")
        all_t = [t for ts in per_day.values() for t in ts]
        out.append(_signal("load", "load:per_day", 2 if len(per_day[busiest]) >= 3 else 3, text, today,
                           tasks=all_t, labels=[f"{len(per_day[busiest])} urgent tasks {fmt(busiest)}"]))
    return out


def _field_status(s: dict) -> list:
    from app.services.intelligence_service.prompts.components import _moisture_words, _stress_words
    today, out = s["today"], []
    for f in s["fields"]:
        parts = [f["crop_status"], "bare field (nothing sown yet)" if f["bare"] else "crop in the ground",
                 f"field condition {f['health'] or 'unknown'}"]
        if f["moisture"] is not None:
            parts.append(f"soil moisture {_moisture_words(f['moisture'])}")
        if f["stress"] is not None:
            parts.append(f"stress {_stress_words(f['stress'])}")
        disease = str(f["disease"]).lower() if f["disease"] not in (None, "", "none") else "unknown"
        parts.append(f"disease risk {disease}")
        text = f"{f['name']}: " + "; ".join(parts) + "."
        sev = 2 if (f["health"] or "").lower() in ("alert", "critical") else 4
        out.append(_signal("field_status", f"field:{f['id']}", sev, text, today, fields=[f["id"]],
                           labels=[f["name"]]))
    return out


def build_from(snapshot: dict) -> list[dict]:
    """All signals, most urgent first, with ids S1..Sn."""
    signals = []
    for builder in (_deadlines, _dependencies, _weather, _plan_changes, _load, _field_status):
        try:
            signals += builder(snapshot)
        except Exception as exc:          # one broken source must not cost all signals
            logger.exception("Signals: %s failed — %s", builder.__name__, exc)
    signals.sort(key=lambda x: (x["severity"], KIND_ORDER.index(x["kind"]), x["dates"][:1] or ["9999"], x["key"]))
    for i, sig in enumerate(signals, 1):
        sig["id"] = f"S{i}"
    return signals


def build_signals(user_id: int, today: date | None = None) -> list[dict]:
    return build_from(collect(user_id, today))


def prompt_lines(signals: list[dict]) -> str:
    """Signals as the model sees them: '[S3] (dependency) text'."""
    return "\n".join(f"[{s['id']}] ({s['kind']}) {s['text']}" for s in signals)
