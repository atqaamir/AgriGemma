"""Rule-based chat answer when no AI model answers (both Gemma and the fallback model down).

No AI: built from the same context the AI would get – the plan (sowing status and dates per
crop, the plan's adjustment text, Not Feasible crops), the forecast-vs-normal block (rain
days, rule reasons, typical / unusual) and the pending tasks.
- Planting / sowing questions: per crop, sowing status and date; a moved sowing as from → to
  with the reason. Not Feasible crops are named as such, never as active.
- Task questions: tasks due today and tomorrow (and overdue ones), in priority order.
- Anything else: "I can't reach the AI right now" + the core summary.
Every answer ends with CLOSING.
"""
from datetime import date, timedelta

from app.utils import clock

CLOSING = "The plan re-checks the forecast every morning; the decision is yours."
NO_AI = "I can't reach the AI right now; here's what your plan says."
_PLANT_WORDS = ("sow", "plant", "seed", "harvest", "boni", "bona")
_TASK_WORDS = ("task", "to do", "todo", "kaam", "urgent", "overdue", "priority", "what should i do",
               "what else should i do")
_PRIORITY = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def _fmt(d: date) -> str:
    return f"{d.day} {d.strftime('%b')}"


def _iso(s: str) -> str:
    return _fmt(date.fromisoformat(s))


def _first_clause(text: str) -> str:
    t = (text or "").split(";")[0].strip().rstrip(".")
    return t[:1].lower() + t[1:] if t else ""


def _mm_list(values: list) -> str:
    vals = [f"{v:g}" for v in values]
    if len(vals) <= 1:
        return f"{vals[0]} mm" if vals else ""
    return f"{', '.join(vals[:-1])} and {vals[-1]} mm"


def _sowing_reason(change: dict, crop: dict, fvn: dict | None) -> str:
    """Why the sowing moved: the heavy-rain / waterlogging facts from the weather block if that
    rule decided, the other blocking rules by day, else the plan's own adjustment text."""
    from app.services.forecast_vs_normal_service import _day_range
    rules = change.get("rules") or []
    wet = next((r for r in rules if r.get("rain_days")), None)
    parts = []
    if wet:
        rain = (fvn or {}).get("rain_by_day") or {}
        rain_days = sorted(wet["rain_days"])
        amounts = _mm_list([rain[d] for d in rain_days if d in rain])
        parts.append(f"heavy rain on {_day_range(rain_days)}" + (f" ({amounts})" if amounts else "")
                     + f": the seed bed is waterlogged on {_day_range(wet['days'])} (soil moisture >60 %)"
                     + (f" – {_first_clause(wet['reasoning'])}" if wet.get("reasoning") else ""))
        others = [r for r in rules if r is not wet]
        if others:
            by_days = {}
            for r in others:
                by_days.setdefault(_day_range(r["days"]), []).append(r["rule"])
            parts.append("; ".join(f"on {days} also {', '.join(labels)}" for days, labels in by_days.items()))
        return "; ".join(parts)
    note = crop.get("sowing_note") or ""
    if " – " in note and note.startswith("Sowing set to"):
        return note.split(" – ", 1)[1]
    if rules:
        by_days = {}
        for r in rules:
            by_days.setdefault(_day_range(r["days"]), []).append(r["rule"])
        return "; ".join(f"{days} unsuitable ({', '.join(labels)})" for days, labels in by_days.items())
    return note or "the forecast changed"


def sowing_lines(plan: dict, fvn: dict | None) -> list:
    changes = {}
    for p in (fvn or {}).get("plan_changes") or []:
        if p.get("event") == "sowing" and p.get("from") and p["from"] != p["to"]:
            changes[p["crop"]] = p
    lines = []
    for c in plan.get("crops") or []:
        name = c["crop"]
        where = f" ({c['field']})" if c.get("field") else ""
        if c.get("not_feasible"):
            reason = (c.get("reason") or "").split(" - ")[0].strip().rstrip(".")
            lines.append(f"- {name}{where}: Not Feasible this season" + (f" ({reason})" if reason else "")
                         + " – not planned, nothing to sow.")
        elif c.get("sown_on"):
            lines.append(f"- {name}{where}: sown on {c['sown_on']}.")
        elif not c.get("sowing"):
            lines.append(f"- {name}{where}: no sowing day set – {c.get('sowing_note') or 'decision needed'}.")
        elif name in changes:
            ch = changes[name]
            lines.append(f"- {name}{where}: sowing moved from {_iso(ch['from'])} to {_iso(ch['to'])}: "
                         f"{_sowing_reason(ch, c, fvn)}.")
        else:
            lines.append(f"- {name}{where}: sowing on {c['sowing']}, as planned.")
    return lines


def weather_line(fvn: dict | None) -> str:
    if not fvn:
        return ""
    f, n = fvn["forecast"], fvn["normal"]
    if fvn["verdict"] == "unusual":
        return (f"The forecast is unusual for {fvn['month']}: {f['rain_mm']:g} mm of rain in 7 days against the "
                f"app's normal of {n['rain_mm']:g} mm for the whole month.")
    return (f"The forecast change is within the usual range for early {fvn['month']} "
            f"({f['rain_mm']:g} mm of rain on {f['rain_days']} days this week).")


def _due_tasks(user_id: int, today: date) -> list:
    from app.repositories.task_repository import TaskRepository
    tomorrow = today + timedelta(days=1)
    due = [t for t in TaskRepository.get_pending(user_id) if t.due_date and t.due_date <= tomorrow]
    due.sort(key=lambda t: (t.due_date >= today, _PRIORITY.get((t.priority or "").lower(), 9), t.due_date))
    return due


def task_lines(user_id: int, today: date) -> list:
    tomorrow = today + timedelta(days=1)
    lines = []
    for t in _due_tasks(user_id, today):
        when = ("overdue" if t.due_date < today else
                f"today ({_fmt(today)})" if t.due_date == today else f"tomorrow ({_fmt(tomorrow)})")
        lines.append(f"- {t.title} – {t.priority}, {when}")
    return lines


def build(user_id: int, message: str, context: dict) -> str:
    m = (message or "").lower()
    intent = context.get("intent")
    plan = context.get("plan") or {}
    fvn = context.get("forecast_vs_normal")
    today = clock.today()

    if intent == "planting" or any(w in m for w in _PLANT_WORDS):
        lines = sowing_lines(plan, fvn)
        if lines:
            head = ["Your plan for sowing:"]
            wl = weather_line(fvn)
            return "\n".join(head + lines + ([wl] if wl else []) + [CLOSING])

    if intent == "task" or any(w in m for w in _TASK_WORDS):
        lines = task_lines(user_id, today)
        head = ["Your tasks for today and tomorrow, most urgent first:"] if lines else \
               ["No tasks are due today or tomorrow."]
        return "\n".join(head + lines + [CLOSING])

    parts = [NO_AI]
    wl = weather_line(fvn)
    if wl:
        parts.append(wl)
    parts += sowing_lines(plan, fvn)
    due = _due_tasks(user_id, today)
    if due:
        n_today = sum(1 for t in due if t.due_date <= today)
        top = due[0]
        parts.append(f"Tasks: {n_today} due today or overdue, {len(due) - n_today} tomorrow; most urgent: "
                     f"{top.title} ({top.priority}).")
    parts.append(CLOSING)
    return "\n".join(parts)
