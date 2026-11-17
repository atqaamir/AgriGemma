"""AI explanations for plan tasks: the rules decide the task and its date, the AI explains why.

One batched AI call per user and run (fast provider, JSON) for the plan tasks that were
created, moved or reactivated, plus up to MAX_BATCH pending plan tasks that still have no
explanation (self-healing after a timeout). The model only gets rule facts (event, crop,
field, due date, the plan's adjustment text, extra/regular session, forecast values) and
writes 1–2 sentences. An explanation that names another date than the due date is dropped.
"""
import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError as _Timeout
from datetime import date, timedelta

from app.extensions import db
from app.models.task import Task
from app.utils import clock

logger = logging.getLogger(__name__)

TIMEOUT_S = 8.0     # the run never waits longer than this for the explanations
MAX_BATCH = 10      # tasks per AI call
PLAN_TASK_CATEGORY = "plan"
DROPPED = ""        # explanation dropped by the date guard: not retried (None = not tried yet)

from app.utils.date_guard import DATE_PATTERNS as _DATE_PATTERNS, dates_in  # noqa: F401  (shared guard)


def mentions_other_date(text: str, due: date) -> bool:
    """True if the text names any date other than `due`."""
    return any((d, m) != (due.day, due.month) for d, m in dates_in(text))


def _strip_other_dates(text: str, due: date) -> str:
    """Facts for the model: other dates become 'an earlier day' / 'a later day'."""
    def repl(m):
        ds = dates_in(m.group(0))
        if not ds or ds[0] == (due.day, due.month):
            return m.group(0)
        d, mo = ds[0]
        other = date(due.year, mo, d) if (mo, d) != (2, 29) else due
        return "an earlier day" if other < due else "a later day"
    for pat, _ in _DATE_PATTERNS:
        text = pat.sub(repl, text or "")
    return text


# ── Facts ──────────────────────────────────────────────────────────────────────

def _plan_index(user_id: int) -> dict:
    """seasonal entry id → (weekly plan entry, its events)."""
    from app.repositories.weekly_plan_repository import WeeklyPlanRepository
    from app.services.plan_override_service import PlanOverrideService
    plan = WeeklyPlanRepository.get_active_by_user_id(user_id)
    index = {}
    for wentry in (plan.entries if plan else []):
        entry = PlanOverrideService.match_entry(user_id, wentry.crop_id, wentry.field_id, warn=False)
        if entry is not None:
            index[entry.id] = (wentry, json.loads(wentry.week_events or "[]"))
    return index


def task_facts(task: Task, index: dict, region: str | None) -> dict:
    """The rule facts behind one plan task (no other date than the due date)."""
    from app.models.seasonal_plan import SeasonalPlanEntry
    from app.models.weather_forecast import WeatherForecast
    from app.services.task_generation_service import PLAN_EVENT_TASKS_BY_TYPE, rule_shift_reason

    due = task.due_date
    etype = PLAN_EVENT_TASKS_BY_TYPE.get(task.task_type, task.task_type)
    wentry, events = index.get(task.seasonal_plan_entry_id, (None, []))
    event = next((e for e in events if e.get("event_type") == etype and e.get("date") == due.isoformat()), {})
    facts = {
        "task_id": task.id, "task": task.title, "event": etype,
        "crop": task.crop.name if task.crop else task.title.split(" – ")[0].split(" ", 1)[-1],
        "field": task.field.name if task.field else None,
        "due_date": f"{due.strftime('%A')} {due.day} {due.strftime('%B %Y')}",
    }
    rule = None
    if etype == "sowing" and wentry is not None:
        adj = json.loads(wentry.climate_adjustments or "[]")
        rule = next((a.get("adjustment") for a in adj if a.get("factor") == "sowing_window"), None)
    elif etype == "irrigation":
        rule = (f"extra irrigation session added by a rule — {event.get('reason')}" if event.get("extra")
                else "regular irrigation session from the crop's irrigation schedule")
    elif etype in ("fertilization", "harvesting"):
        entry = SeasonalPlanEntry.query.get(task.seasonal_plan_entry_id) if task.seasonal_plan_entry_id else None
        rule = rule_shift_reason(entry, etype, due) or f"{etype} date from the seasonal plan"
    if rule:
        facts["rule"] = _strip_other_dates(rule, due)
    if region:
        fc = WeatherForecast.query.filter_by(region=region, date=due).first()
        if fc:
            facts["forecast_on_due_date"] = {
                "avg_temperature": f"{fc.avg_temperature_c:g} °C", "rain": f"{fc.rainfall_mm or 0:g} mm",
                "sunlight": f"{fc.sunlight_hours:g} h", "humidity": f"{fc.humidity:g} %"}
    return facts


# ── Prompt and call ────────────────────────────────────────────────────────────

_SYSTEM = (
    "You explain farm tasks to a farmer. The farm's rules already decided each task and its date; "
    "you only explain why the task is on that day.\n"
    "Rules: use only the facts given. Write 1–2 plain sentences per task. Do not change the date or the "
    "action, and add no advice beyond the facts. Mention no date other than the task's due date: only "
    "if the facts mention other days, call them 'the days before'; never invent reasons about other "
    "days. Write values as digits with units (32 °C, 0 mm, 10 h) and scores in "
    "words. Do not open with "
    "'I understand' or 'I know', and never say 'you must'.\n"
    'Answer with JSON only: {"<task_id>": "<explanation>", ...} for every task_id given.'
)


def build_prompt(facts: list[dict]) -> str:
    from app.services.intelligence_service.chatbot_service.prompts._prompt_chatbot_service import _SYSTEM_SEP
    return f"{_SYSTEM}{_SYSTEM_SEP}TASKS (rule facts):\n{json.dumps(facts, ensure_ascii=False, indent=1)}"


def _call_ai(prompt: str, facts: list[dict]) -> str:
    """One fast-provider JSON call (replaced in tests). The placeholder provider (local runs
    without a model) gets a fixed explanation built from the rule facts instead."""
    from app.services.ai_model_service import ai_model_service
    provider = ai_model_service._fast_provider or ai_model_service.get_provider()
    if provider.name.startswith("Placeholder"):
        return json.dumps({str(f["task_id"]): f"{f['task']} is planned for this day by the farm's rules"
                           + (f": {f['rule']}" if f.get("rule") else ".") for f in facts})
    return ai_model_service.fast_complete_direct(prompt)


def _call_with_limit(prompt: str, facts: list[dict]) -> str | None:
    pool = ThreadPoolExecutor(max_workers=1)
    future = pool.submit(_call_ai, prompt, facts)
    try:
        return future.result(timeout=TIMEOUT_S)
    except _Timeout:
        logger.warning("Plan task explanations: no AI answer within %.0f s — left empty", TIMEOUT_S)
    except Exception as exc:
        logger.warning("Plan task explanations: AI call failed (%s) — left empty", exc)
    finally:
        pool.shutdown(wait=False)
    return None


def _parse(raw: str | None) -> dict:
    if not raw:
        return {}
    text = raw.strip()
    m = re.search(r"\{.*\}", text, re.S)
    try:
        data = json.loads(m.group(0) if m else text)
    except (ValueError, AttributeError):
        logger.warning("Plan task explanations: answer is not JSON — left empty")
        return {}
    return {str(k): v for k, v in data.items() if isinstance(v, str)} if isinstance(data, dict) else {}


def explain(user_id: int, changed_tasks: list) -> dict:
    """Explain the changed plan tasks (+ pending ones still without an explanation) in one
    AI call. Returns {"called": bool, "explained": [ids], "dropped": [ids], "failed": [ids]}."""
    from app.services.domain_service.user_service import UserService

    result = {"called": False, "explained": [], "dropped": [], "failed": []}
    ids, batch = set(), []
    for t in changed_tasks:
        if t is not None and t.id not in ids and t.task_category == PLAN_TASK_CATEGORY and t.is_pending:
            batch.append(t)
            ids.add(t.id)
    missing = (Task.query.filter(Task.user_id == user_id, Task.task_category == PLAN_TASK_CATEGORY,
                                 Task.completed.is_(False), Task.is_active.is_(True),
                                 Task.ai_explanation.is_(None))
               .order_by(Task.due_date, Task.id).all())
    batch += [t for t in missing if t.id not in ids]
    batch = batch[:MAX_BATCH]
    if not batch:
        return result

    index = _plan_index(user_id)
    region = UserService.get_user_location(user_id)
    facts = [task_facts(t, index, region) for t in batch]
    result["called"] = True
    answers = _parse(_call_with_limit(build_prompt(facts), facts))
    for t in batch:
        text = (answers.get(str(t.id)) or "").strip()
        if not text:
            t.ai_explanation = None                      # not answered: retried next run
            result["failed"].append(t.id)
        elif mentions_other_date(text, t.due_date):
            logger.warning("Plan task %s: explanation names another date than %s — dropped: %r",
                           t.id, t.due_date, text[:160])
            t.ai_explanation = DROPPED
            result["dropped"].append(t.id)
        else:
            t.ai_explanation = text
            result["explained"].append(t.id)
    db.session.commit()
    logger.info("Plan task explanations for user=%s: %s", user_id, result)
    return result
