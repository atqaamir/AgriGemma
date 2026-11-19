"""Text of the change notifications (alert detail + change-summary pop-up) after a re-plan.

  facts (no AI: plan, forecast vs. normal, task changes)
    → rule_text(facts): always available, shown when the AI text is missing or rejected
    → ai_text(user_id, facts): one fast_complete_direct call (minimal thinking, temperature 0.1),
      checked by ai_text_guard (leaked drafts, crops the user doesn't have, tone, dates).
"""
from __future__ import annotations

import logging
import re
from datetime import date

from app.utils import clock

logger = logging.getLogger(__name__)

MAX_TOKENS = 300
CALL_TIMEOUT_S = 12.0
_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")


def _fmt(d: date) -> str:
    return f"{d.day} {d.strftime('%b')}"


def _iso_to_text(s: str) -> str:
    return _ISO.sub(lambda m: _fmt(date(int(m.group(1)), int(m.group(2)), int(m.group(3)))), s or "")


def facts(user_id: int, task_summaries: list, farmer: str = "Farmer") -> dict:
    """Everything the notification may say, built without AI."""
    from app.services import forecast_vs_normal_service as fvn_service
    from app.services.intelligence_service.chatbot_service.fallback_answer import sowing_lines, weather_line
    from app.services.intelligence_service.context.context_builder import _fetch_plan

    today = clock.today()
    try:
        fvn = fvn_service.build(user_id, today)
    except Exception as exc:
        logger.warning("change notification facts: forecast vs. normal failed (%s)", exc)
        fvn = None
    try:
        plan = _fetch_plan(user_id) or {}
    except Exception as exc:
        logger.warning("change notification facts: plan failed (%s)", exc)
        plan = {}
    moved = {p["crop"] for p in (fvn or {}).get("plan_changes") or []
             if p.get("event") == "sowing" and p.get("from") and p["from"] != p["to"]}
    sowing = [l[2:] for l in sowing_lines(plan, fvn) if "Not Feasible" not in l]
    shifts = [p for p in (fvn or {}).get("plan_changes") or [] if p.get("event") != "sowing" and p.get("from")]
    # Later dates of a crop whose sowing moved follow it: one sentence instead of every date.
    other = [f"{p['event'].capitalize()} for {p['crop']} moved from {_iso_to_text(p['from'])} to "
             f"{_iso_to_text(p['to'])}." for p in shifts if p["crop"] not in moved]
    if any(p["crop"] in moved for p in shifts):
        other.append("Irrigation, fertilization and harvest dates move with the new sowing dates.")
    tasks = [f"{t['title']}{' (' + t['field'] + ')' if t.get('field') else ''}: "
             f"{_iso_to_text(', '.join(t['changes']))}" for t in task_summaries]
    dates = {today}
    for p in (fvn or {}).get("plan_changes") or []:
        for k in ("from", "to"):
            if p.get(k):
                dates.add(date.fromisoformat(p[k]))
    for d in ((fvn or {}).get("rain_by_day") or {}):
        dates.add(date.fromisoformat(d))
    for c in plan.get("crops") or []:
        for k in ("sowing", "irrigation_start", "fertilization", "harvest", "sown_on"):
            if c.get(k):
                dates.add(c[k])                   # "10 May" strings: matched as (day, month) below
    return {
        "farmer": farmer, "today": f"{today.strftime('%A')} {today.day} {today.strftime('%B')}",
        "verdict": (fvn or {}).get("verdict"), "fvn": fvn, "weather_line": weather_line(fvn),
        "moved_crops": sorted(moved), "sowing": sowing, "other_changes": other, "tasks": tasks,
        "allowed_dates": _dates(dates, today.year),
    }


def _dates(values, year) -> set:
    from app.utils.date_guard import dates_in
    out = set()
    for v in values:
        if isinstance(v, date):
            out.add((v.day, v.month))
        else:
            out.update(dates_in(str(v)))
    return out


def rule_text(f: dict) -> str:
    from app.services.intelligence_service.chatbot_service.fallback_answer import CLOSING
    parts = []
    if f.get("weather_line"):
        parts.append(f["weather_line"])
    parts += f.get("sowing") or []
    parts += f.get("other_changes") or []
    if not f.get("sowing") and not f.get("other_changes") and f.get("tasks"):
        n = len(f["tasks"])
        parts.append(f"{n} task{'s' if n != 1 else ''} changed: " + "; ".join(f["tasks"][:3]) + ".")
    parts.append(CLOSING)
    return " ".join(parts)


_SYSTEM = (
    "You write one short notification for a farmer about a change to their farm plan. "
    "Use only the FACTS. Write 2–3 plain sentences addressed to the farmer: what changed and why. "
    "No lists, no headings, no notes about how you write, no drafts – only the final notification text. "
    "Name only crops, fields and dates that are in the FACTS. Never say 'you must'."
)


def build_prompt(f: dict) -> str:
    from app.services.intelligence_service.chatbot_service.prompts._prompt_chatbot_service import _SYSTEM_SEP
    lines = [f"Farmer: {f['farmer']}", f"Today: {f['today']}"]
    if f.get("weather_line"):
        lines.append(f"Weather: {f['weather_line']}")
    if f.get("sowing"):
        lines.append("Sowing:\n" + "\n".join(f"- {s}" for s in f["sowing"]))
    if f.get("other_changes"):
        lines.append("Other plan changes:\n" + "\n".join(f"- {s}" for s in f["other_changes"]))
    if f.get("tasks"):
        lines.append("Task changes:\n" + "\n".join(f"- {s}" for s in f["tasks"]))
    return f"{_SYSTEM}{_SYSTEM_SEP}FACTS:\n" + "\n".join(lines)


def _call_ai(prompt: str) -> str | None:
    """One direct call (replaced in tests). The placeholder provider (no model) gets None, so
    the rule-based text is used."""
    from app.services.ai_model_service import ai_model_service
    provider = ai_model_service._fast_provider or ai_model_service.get_provider()
    if provider.name.startswith("Placeholder"):
        return None
    return ai_model_service.fast_complete_direct(prompt, max_tokens=MAX_TOKENS, timeout=CALL_TIMEOUT_S,
                                                 temperature=0.1)


def ai_text(user_id: int, f: dict) -> tuple[str, str]:
    """(text, source): source "ai" or "rules" (no answer / rejected by the guard)."""
    from app.utils import ai_text_guard
    try:
        raw = (_call_ai(build_prompt(f)) or "").strip()
    except Exception as exc:
        logger.warning("change notification: AI call failed (%s) – rule-based text", exc)
        raw = ""
    if raw and not ai_text_guard.check_for_user(raw, user_id, "change notification",
                                                verdict=f.get("verdict"), allowed_dates=f.get("allowed_dates")):
        return raw, "ai"
    return rule_text(f), "rules"
