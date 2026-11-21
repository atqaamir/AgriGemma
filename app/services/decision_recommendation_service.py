"""AI recommendation for "decision needed" / overdue sowing (the "Decide: <crop> sowing" tasks).

The code collects the facts per decision (sowing window, the unsuitable days and why, the
forecast outlook, the crop's sowing-to-harvest time from the plan, the first suitable day
after the window and the harvest date it gives, the four options); ONE batched AI call
(minimal thinking) recommends one option with a 2–3 sentence reason. The behaviour guidance
is part of the facts block.

Every answer is checked: the shared AI-text guard (drafts, crops, tone, dates only from the
facts), one of the four options, 2–3 sentences, every number must appear in the facts, and no
agronomic claims (yield, pests, varieties, …) that are not in the facts. Rejected or missing
answers: no recommendation - the task and the notification show the options only.

Stored on the decision task (ai_explanation; DROPPED = "" when there is none) and in the
decision notification's detail. Runs in the background after a simulator click
(deferred_ai_service) and in the same step at the 5 AM daily update.
"""
import json
import logging
import re
from datetime import date, datetime, timedelta

from app.extensions import db
from app.models.task import Task
from app.utils import clock

logger = logging.getLogger(__name__)

LABEL = "Recommendation – the decision is yours"
NO_RECOMMENDATION = "No AI recommendation – choose one of the options."
DROPPED = ""
OPTIONS = {
    "sow_anyway":     "Sow anyway with precautions",
    "short_duration": "Switch to a short-duration variety",
    "switch_crop":    "Switch crop",
    "skip_season":    "Skip the season",
}
DECISION_TASK_TYPE = "decision"
MAX_TOKENS = 600
CALL_TIMEOUT_S = 12
BACKGROUND_TIMEOUT_S = 30.0

GUIDANCE = (
    "Recommend exactly ONE option per decision, by its key. Prefer the option that the facts support most "
    "directly (see 'Options – what the app knows'). Do not treat the original planned harvest date as a target "
    "unless the facts say why. For an option marked 'not modelled', the app has no facts about its effect: do not "
    "claim an effect for it. Give the reason in 2–3 plain sentences "
    "addressed to the farmer. Use only the facts above: the dates, numbers and reasons given there. "
    "Do not add agronomic claims that are not in the facts (no yields, losses, prices, pests, diseases, "
    "germination, seed rates, fertiliser or variety names), and do not name other crops. "
    "Do not promise an outcome. Do not say that the decision is yours (the app adds that). "
    "Calm and factual; never say 'you must'."
)

# Agronomic claim words: allowed only when the facts use them.
_CLAIM_WORDS = re.compile(
    r"\b(yields?|loss(?:es)?|profits?|prices?|markets?|pests?|diseases?|insects?|fung\w*|germinat\w*|"
    r"seed rates?|fertili[sz]\w*|pesticid\w*|herbicid\w*|kg|acres?|hectares?|varieties|"
    r"bt\b|hybrid\w*|percent)\b", re.I)
# A named variety ("variety FH-142", "variety Bt Cyto"): case-sensitive, so "variety may" is not one.
_VARIETY_NAME = re.compile(r"\bvariet(?:y|ies)\s+(?:called\s+|named\s+)?[A-Z][\w-]*")
_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")


# ── facts ────────────────────────────────────────────────────────────────────────────
def _fmt(d: date) -> str:
    return f"{d.day} {d.strftime('%b')}"


def _parse_mdy(s):
    return datetime.strptime(s, "%m/%d/%Y").date() if s else None


def _day_check(entry_crop_id, stage_id, location, day, field_moisture, field_ph):
    """(suitable, reasons, weather) for one forecast day - the rule engine's own check."""
    from app.rules.rule_engine.rule_engine import RuleEngine
    lookup = RuleEngine.get_forecast_by_region_and_date
    w = lookup(location, day)
    if not w:
        return None, ["no forecast"], None
    wet = RuleEngine._seedbed_wet(location, day, lookup)
    blocking, bands = RuleEngine._assess_sowing_day(entry_crop_id, stage_id, w, field_moisture, field_ph,
                                                    seedbed_wet=wet)
    reasons = [RuleEngine._band_text(f, bands[f]) + (RuleEngine.SEEDBED_WET_NOTE if wet and f == "soil_moisture"
                                                     else "") for f in blocking]
    return not blocking, reasons, w


def facts_for_task(task: Task, today: date | None = None) -> dict | None:
    """Facts for one decision task (None if its entry / window is gone)."""
    from app.models.seasonal_plan import SeasonalPlanEntry
    from app.repositories.weekly_plan_repository import WeeklyPlanRepository
    from app.rules.rule_engine.rule_engine import RuleEngine
    from app.services.domain_service.user_service import UserService
    from app.services.plan_override_service import PlanOverrideService

    today = today or clock.today()
    entry = SeasonalPlanEntry.query.get(task.seasonal_plan_entry_id) if task.seasonal_plan_entry_id else None
    planned = _parse_mdy(entry.sowing) if entry else None
    if not planned:
        return None
    window_end = planned + timedelta(days=RuleEngine.MAX_SOWING_DELAY_DAYS)
    crop = entry.crop_name_rel.name if entry.crop_name_rel else "the crop"
    field = task.field
    location = (field.location if field else None) or UserService.get_user_location(task.user_id)
    moisture = field.moisture_level if field else None
    ph = field.ph_level if field else None
    harvest = _parse_mdy(entry.harvesting)
    duration = (harvest - planned).days if harvest else None
    stage_id = None
    plan = WeeklyPlanRepository.get_active_by_user_id(task.user_id)
    for we in (plan.entries if plan else []):
        if we.crop_id == entry.crop_name_id:
            stage_id = we.growth_stage_id
    crop_id = entry.crop_name_id
    overdue = today > window_end
    status = ("Sowing overdue: the sowing window has passed and sowing was not recorded as done"
              if overdue else "Decision needed: no suitable sowing day left in the sowing window")

    days, unsuitable, first_ok = [], [], None
    for i in range(7):
        d = today + timedelta(days=i)
        ok, reasons, w = _day_check(crop_id, stage_id, location, d, moisture, ph)
        if w is None:
            continue
        weather = (f"{w.get('avg_temperature_c'):g} °C, {w.get('rainfall_mm') or 0:g} mm rain, "
                   f"{w.get('sunlight_hours'):g} h sun, humidity {w.get('humidity'):g} %")
        in_window = d <= window_end
        days.append(f"{_fmt(d)}: {weather} – {'suitable' if ok else 'unsuitable (' + ', '.join(reasons) + ')'}"
                    f" for {crop} sowing{' (inside the window)' if in_window else ' (after the window)'}")
        if not ok and in_window:
            unsuitable.append(d)
        if ok and first_ok is None and (d > window_end or overdue):
            first_ok = d
    last_fc = today + timedelta(days=6)
    first_line = (f"First suitable sowing day in the forecast: {_fmt(first_ok)} "
                  f"({(first_ok - window_end).days} day(s) after the window ends)"
                  if first_ok else f"No suitable sowing day in the forecast (up to {_fmt(last_fc)})")
    new_harvest = first_ok + timedelta(days=duration) if first_ok and duration else None
    harvest_line = (f"Harvest if sown on {_fmt(first_ok)}: about {_fmt(new_harvest)}" if new_harvest else None)
    months = harvest_months(crop)                       # (crop type name, [month numbers]) or None
    field_name = field.name if field else "this field"
    if first_ok:
        sow = (f"first suitable sowing day in the forecast: {_fmt(first_ok)}, "
               f"{(first_ok - window_end).days} day(s) after the window ends")
        if new_harvest:
            sow += f"; harvest about {_fmt(new_harvest)}"
            if months:
                inside = new_harvest.month in months[1]
                sow += (f", {'within' if inside else 'outside'} the harvest months of {months[0]} crops in the "
                        f"rule base ({_month_range(months[1])})")
    else:
        sow = (f"no suitable sowing day in the forecast up to {_fmt(last_fc)}; sowing on an unsuitable day goes "
               f"against the sowing rules for {crop}")
    option_facts = {
        "sow_anyway": sow,
        "short_duration": "needs different seed; the app has no variety data, so the effect on harvest is not modelled",
        "switch_crop": "needs a new seasonal plan entry; not modelled",
        "skip_season": f"no {crop} this season on {field_name}",
    }
    try:
        from app.services import forecast_vs_normal_service as fvn
        data = fvn.build(task.user_id, today)
        verdict = (f"{data['verdict']} for {data['month']}" if data
                   else "no change from the app's normal forecast for the season")
    except Exception:
        verdict = None
    allowed = {today + timedelta(days=i) for i in range(7)} | {planned, window_end}
    if harvest:
        allowed.add(harvest)
    if first_ok and duration:
        allowed.add(first_ok + timedelta(days=duration))
    f = {
        "key": str(task.id), "crop": crop, "field": field.name if field else None, "status": status,
        "today": _fmt(today), "window": f"{_fmt(planned)}–{_fmt(window_end)} (planned date + "
                                         f"{RuleEngine.MAX_SOWING_DELAY_DAYS} days)",
        "unsuitable": [_fmt(d) for d in unsuitable], "days": days, "verdict": verdict,
        "duration": f"{duration} days from sowing to harvest (seasonal plan)" if duration else None,
        "first_ok": first_line, "harvest_if_first_ok": harvest_line, "options": option_facts,
        "first_ok_date": first_ok,
        "allowed_dates": sorted(allowed),
    }
    f["text"] = _facts_text(f)
    return f


def first_suitable_day(task: Task, today: date | None = None) -> date | None:
    """The first suitable sowing day in the forecast after the window (the 'sow anyway' fact of
    the recommendation), or None when the forecast has none."""
    f = facts_for_task(task, today)
    return f.get("first_ok_date") if f else None


def _facts_text(f: dict) -> str:
    lines = [f"Decision {f['key']}: {f['crop']}" + (f" on {f['field']}" if f["field"] else ""),
             f"- Today: {f['today']}", f"- Status: {f['status']}", f"- Sowing window: {f['window']}"]
    if f["unsuitable"]:
        lines.append(f"- Unsuitable days left in the window: {', '.join(f['unsuitable'])}")
    if f["verdict"]:
        lines.append(f"- Forecast compared with the season: {f['verdict']}")
    lines.append("- Forecast by day (the rules' sowing check):")
    lines += [f"  - {d}" for d in f["days"]]
    if f["duration"]:
        lines.append(f"- Crop: {f['duration']}")
    lines.append(f"- {f['first_ok']}")
    if f["harvest_if_first_ok"]:
        lines.append(f"- {f['harvest_if_first_ok']}")
    lines.append("- Options – what the app knows:")
    lines += [f"  - {k} ({OPTIONS[k].lower()}): {v}" for k, v in f["options"].items()]
    return "\n".join(lines)


def harvest_months(crop: str):
    """(crop type name, harvest month numbers) from the rule base (crop_type_timeline), or None."""
    try:
        from app.rules.vocabulary.crop_type import CropType
        from app.services.rule_base_service import rule_base_service
        type_id = rule_base_service.get_crop_type_by_crop(crop)
        tl = rule_base_service.get_timeline_by_crop_type(type_id) if type_id else None
        if tl is None:
            return None
        a, b = tl.harvest_start_month, tl.harvest_end_month
        months = list(range(a, b + 1)) if a <= b else list(range(a, 13)) + list(range(1, b + 1))
        ct = CropType.query.get(type_id)
        return (ct.name if ct else "this crop type"), months
    except Exception:
        logger.exception("harvest months for %s", crop)
        return None


def _month_range(months: list) -> str:
    import calendar
    names = [calendar.month_abbr[m] for m in months]
    return names[0] if len(names) == 1 else f"{names[0]}–{names[-1]}"


def build_prompt(facts: list[dict]) -> str:
    from app.services.intelligence_service.chatbot_service.prompts._prompt_chatbot_service import _SYSTEM_SEP
    system = ("You help a farmer with a sowing decision. Answer with JSON only: "
              '{"<decision number>": {"option": "<option key>", "reason": "<2-3 sentences>"}}.')
    opts = "\n".join(f"- {k}: {v}" for k, v in OPTIONS.items())
    body = "\n\n".join(f["text"] for f in facts)
    return f"{system}{_SYSTEM_SEP}FACTS:\n{body}\n\nOptions (keys):\n{opts}\n\nHow to answer: {GUIDANCE}"


# ── checks ───────────────────────────────────────────────────────────────────────────
def _sentences(text: str) -> int:
    return len([s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()])


def problem(answer, f: dict, user_id: int) -> str | None:
    """None if the answer may be shown, else why not."""
    from app.utils import ai_text_guard
    if not isinstance(answer, dict):
        return "no answer"
    option, reason = answer.get("option"), (answer.get("reason") or "").strip()
    if option not in OPTIONS:
        return f"unknown option {option!r}"
    if not reason:
        return "empty reason"
    n = _sentences(reason)
    if not 2 <= n <= 3:
        return f"{n} sentences (2–3 expected)"
    p = ai_text_guard.check_for_user(reason, user_id, "decision recommendation", allowed_dates=f["allowed_dates"])
    if p:
        return p
    facts_numbers = set(_NUMBER.findall(f["text"]))
    extra = [x for x in _NUMBER.findall(reason) if x not in facts_numbers]
    if extra:
        return "number not in the facts: " + ", ".join(extra)
    known = (f["text"] + " " + " ".join(OPTIONS.values())).lower()   # what the model was given
    for m in _CLAIM_WORDS.finditer(reason):
        if m.group(0).lower() not in known:
            return f'agronomic claim not in the facts ("{m.group(0)}")'
    m = _VARIETY_NAME.search(reason)
    if m:
        return f'variety name not in the facts ("{m.group(0)}")'
    return None


def recommendation_text(answer: dict) -> str:
    return f"{OPTIONS[answer['option']]}. {answer['reason'].strip()}"


# ── AI call ──────────────────────────────────────────────────────────────────────────
def _call_ai(prompt: str, timeout: float = CALL_TIMEOUT_S) -> str | None:
    """One direct call with minimal thinking (replaced in tests). The placeholder provider
    (no model) gets None: no recommendation, the options are shown."""
    from app.services.ai_model_service import ai_model_service
    provider = ai_model_service._fast_provider or ai_model_service.get_provider()
    if provider.name.startswith("Placeholder"):
        return None
    return ai_model_service.fast_complete_direct(prompt, max_tokens=MAX_TOKENS, timeout=timeout, temperature=0.1)


def _no_model() -> bool:
    """True for the placeholder provider (no model to ask)."""
    from app.services.ai_model_service import ai_model_service
    provider = ai_model_service._fast_provider or ai_model_service.get_provider()
    return provider.name.startswith("Placeholder")


# ── Lazy retry when the Decide task's details are opened (one call, debounced) ─────────
LAZY_MIN_INTERVAL_S = 60.0
_lazy_lock = __import__("threading").Lock()
_lazy_running: set = set()
_lazy_last: dict = {}            # task id -> monotonic time of the last attempt


def recommend_on_open(user_id: int, task_id: int) -> dict:
    """The Decide task's details were opened and it has no recommendation: one AI call for it,
    at most one at a time per task and one per LAZY_MIN_INTERVAL_S. Returns
    {"status": "stored" | "recommended" | "failed" | "in_progress" | "debounced" | "not_open",
     "text": str | None}."""
    import time
    t = next((x for x in open_decision_tasks(user_id) if x.id == task_id), None)
    if t is None:
        return {"status": "not_open", "text": None}
    if t.ai_explanation:
        return {"status": "stored", "text": t.ai_explanation}
    with _lazy_lock:
        if task_id in _lazy_running:
            return {"status": "in_progress", "text": None}
        last = _lazy_last.get(task_id)
        if last is not None and time.monotonic() - last < LAZY_MIN_INTERVAL_S:
            return {"status": "debounced", "text": None}
        _lazy_running.add(task_id)
        _lazy_last[task_id] = time.monotonic()
    try:
        result = recommend(user_id, task_ids={task_id}, include_dropped=True)
    finally:
        with _lazy_lock:
            _lazy_running.discard(task_id)
    db.session.expire_all()
    t = Task.query.get(task_id)
    ok = task_id in result["recommended"]
    logger.info("Decision recommendation on open, task %s: %s", task_id, "recommended" if ok else result)
    return {"status": "recommended" if ok else "failed", "text": t.ai_explanation if ok else None}


def open_decision_tasks(user_id: int) -> list:
    return (Task.query.filter(Task.user_id == user_id, Task.task_type == DECISION_TASK_TYPE,
                              Task.is_active.is_(True), Task.completed.is_(False))
            .order_by(Task.id).all())


def recommend(user_id: int, write_guard=None, only_missing: bool = True, task_ids=None,
              include_dropped: bool = False) -> dict:
    """Recommend for the user's open decision tasks without a recommendation yet (one AI call).
    Returns {"called", "recommended": [ids], "rejected": {id: reason}, "failed": [ids], "no_model": bool}.
    - The AI is unavailable (HTTP 503/429/timeout on the primary AND the fallback model, an error,
      no usable answer): "failed" – ai_explanation stays None, so the deferred retry and the lazy
      retry (task details opened) try again; the notification shows the options meanwhile.
    - Rejected by the checks, or no model at all (placeholder provider): DROPPED ("") – the options.
    only_missing: tasks without a recommendation (None; also "" with include_dropped).
    task_ids: only these decision tasks.
    write_guard: as plan_task_explanation_service.explain (background runs drop stale answers)."""
    result = {"called": False, "recommended": [], "rejected": {}, "failed": [], "no_model": False}
    tasks = [t for t in open_decision_tasks(user_id)
             if (task_ids is None or t.id in task_ids)
             and (not only_missing or t.ai_explanation is None or (include_dropped and t.ai_explanation == DROPPED))]
    facts = {}
    for t in tasks:
        f = facts_for_task(t)
        if f:
            facts[t.id] = f
    if not facts:
        return result
    result["called"] = True
    timeout = BACKGROUND_TIMEOUT_S if write_guard is not None else CALL_TIMEOUT_S
    unavailable = False
    try:
        raw = _call_ai(build_prompt(list(facts.values())), timeout)
        result["no_model"] = raw is None and _no_model()
    except Exception as exc:
        logger.warning("Decision recommendation for user=%s: AI call failed (%s) – retried later", user_id, exc)
        raw, unavailable = None, True
    from app.utils.ai_json import parse_json_object
    answers = parse_json_object(raw) or {}
    texts, notes = {}, {}
    for tid, f in facts.items():
        a = answers.get(str(tid))
        if a is None:
            result["failed"].append(tid)
            if result["no_model"] and not unavailable:
                texts[tid] = DROPPED                     # no model: the options, nothing to retry
            else:
                texts[tid], notes[tid] = None, DROPPED   # AI unavailable / no usable answer: retried
            continue
        p = problem(a, f, user_id)
        if p:
            logger.warning("Decision recommendation task %s rejected (%s): %r", tid, p, a)
            result["rejected"][tid] = {"reason": p, "answer": a}
            texts[tid] = DROPPED
        else:
            texts[tid] = recommendation_text(a)
            result["recommended"].append(tid)

    def write():
        for t in tasks:
            if t.id in texts:
                t.ai_explanation = texts[t.id]
                _update_notification(t, texts[t.id] if texts[t.id] is not None else notes.get(t.id, DROPPED))
    if write_guard is not None:
        with write_guard() as current:
            if not current:
                db.session.rollback()
                logger.info("Decision recommendation for user=%s: a newer run started - dropped", user_id)
                return {**result, "stale": True}
            write()
            db.session.commit()
    else:
        write()
        db.session.commit()
    logger.info("Decision recommendation for user=%s: %s", user_id, result)
    return result


def detail_suffix(text: str) -> str:
    return f"\n\n{LABEL}: {text}" if text else f"\n\n{NO_RECOMMENDATION}"


def _update_notification(task: Task, text: str) -> None:
    """The latest decision notification of the task's entry gets the recommendation (or the
    'no recommendation' line) after its fixed text."""
    from app.models.notification import Notification
    from app.rules.rule_engine.rule_engine import RuleEngine
    n = (Notification.query.filter(Notification.user_id == task.user_id,
                                   Notification.entity_type == "seasonal_plan_entry",
                                   Notification.entity_id == task.seasonal_plan_entry_id,
                                   Notification.message.in_((RuleEngine.SOWING_OVERDUE_TEXT,
                                                             RuleEngine.SOWING_DECISION_TEXT)))
         .order_by(Notification.id.desc()).first())
    if n is None:
        return
    base = (n.detail or "").split(f"\n\n{LABEL}:")[0].split(f"\n\n{NO_RECOMMENDATION}")[0]
    n.detail = base + detail_suffix(text)
