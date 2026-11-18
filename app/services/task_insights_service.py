"""Task insights (tasks page): one AI call that reads between the lines of the signals.

  signals (insight_signals_service, no AI) + today's/tomorrow's tasks
    → one fast_complete_direct call (minimal thinking, JSON parsed tolerantly)
    → validation (insight_validation): evidence ids, dates, style; priority order limited to
      the real task ids
    → stored in ai_insight_report (kind "task_insights") with the signals and a fingerprint.
Unparseable answer / timeout / error → a rule-based "basic summary" from the top signals.

Output: {"priority_order": [{task_id, title, due, priority, field, reason, source}],
         "insights": [{title, explanation, recommendation, evidence, based_on}],   (max 4)
         "watch": [{text, evidence, based_on}],                                     (max 2)
         "dropped": [{section, item, reason}], "basic_summary": bool, "error": str|None}
"""
from __future__ import annotations

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as _Timeout
from datetime import date, timedelta

from app.services import insight_report_service as reports
from app.services import insight_signals_service as sig
from app.services import insight_validation as val
from app.utils import clock
from app.utils.ai_json import parse_json_object

logger = logging.getLogger(__name__)

KIND = "task_insights"
MAX_INSIGHTS, MAX_WATCH = 4, 2
TIMEOUT_S = 25.0          # whole call incl. one provider retry
MAX_TOKENS = 1500
TEMPERATURE = 0.1        # low: repeated runs on the same data stay consistent
_PRIORITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}
INSIGHT_KINDS = ("deadline", "dependency", "weather", "load", "plan_change")

_SYSTEM = (
    "You are the farm's task advisor. You read the signals below – facts already worked out from the farm's "
    "plan, tasks, forecast and fields – and connect them to say what matters for the farmer's tasks.\n"
    "Rules:\n"
    "1. Use only the signals and the task list. Connect signals that are given; add no facts, numbers, "
    "dates, causes or tasks that are not in them.\n"
    "2. priority_order: every task in TASKS exactly once, in the order you recommend doing them (today's "
    "before tomorrow's). reason: one short line on why it has that place – name the plan event, weather "
    "window or dependency it serves (e.g. \"before the cotton sowing on 9 May\", \"before the showers on "
    "7–8 May\"), not just its priority or due date.\n"
    "3. insights: at most 4, about what affects the tasks: dependencies between tasks and plan events, "
    "weather windows, deadlines, overload. The signals are listed most urgent first. Give EVERY deadline "
    "signal and EVERY dependency signal its own insight (one each, citing it), then weather windows; use "
    "load or plan-change signals only if there is room. Each insight cites at least one signal id in "
    "evidence and mentions only dates that appear in the signals it cites.\n"
    "4. watch: at most 2 things to keep an eye on in the coming days that are NOT already an insight, "
    "each with evidence.\n"
    "5. Recommend, don't decide: never move dates, never create or cancel tasks, never say you changed "
    "something. Phrase recommendations as \"I'd recommend …\" or \"Today's priority is …\".\n"
    "6. Style: refer to tasks by their title, never by task_id. Never write \"I understand\", \"I know\", "
    "\"you must\" or \"must\". Describe scores and risks in words (low / moderate / high), not numbers. "
    "Where nothing is sown (bare field) there are no plants: do not mention leaves, stems or wilting there.\n"
    "Answer with compact JSON only (no code fence, no other text):\n"
    '{"priority_order": [{"task_id": 12, "reason": "..."}], '
    '"insights": [{"title": "max 8 words", "explanation": "1-2 sentences: how the cited signals connect", '
    '"evidence": ["S1", "S3"], "recommendation": "I\'d recommend ..."}], '
    '"watch": [{"text": "one sentence", "evidence": ["S4"]}]}'
)


# ── Inputs ─────────────────────────────────────────────────────────────────────

def candidates(snapshot: dict) -> list[dict]:
    """Pending tasks due today or tomorrow (overdue ones count as today), rule order."""
    today = snapshot["today"]
    tasks = [t for t in snapshot["tasks"] if t["due"] and t["due"] <= today + timedelta(days=1)]
    return sorted(tasks, key=lambda t: (max(t["due"], today), _PRIORITY_RANK.get(t["priority"], 4), t["id"]))


def _task_line(t: dict, today) -> str:
    when = "overdue" if t["due"] < today else sig.rel(t["due"], today)
    where = f", field {t['field']}" if t["field"] else ""
    return f"- task_id {t['id']}: {t['title']} ({t['priority']}, due {when} {sig.fmt(t['due'])}{where})"


def build_prompt(signals: list, cands: list, today) -> str:
    from app.services.intelligence_service.chatbot_service.prompts._prompt_chatbot_service import _SYSTEM_SEP
    day = f"{today.strftime('%A')} {today.day} {today.strftime('%B %Y')}"
    tasks = "\n".join(_task_line(t, today) for t in cands) or "- (no tasks due today or tomorrow)"
    return (f"{_SYSTEM}{_SYSTEM_SEP}TODAY: {day}\n\nSIGNALS:\n{sig.prompt_lines(signals)}\n\n"
            f"TASKS (today and tomorrow):\n{tasks}")


# ── AI call (replaced in tests) ────────────────────────────────────────────────

def _placeholder_answer(signals: list, cands: list) -> str:
    """Placeholder provider (no model): a fixed answer built from the signals, so the parse →
    validate → store path runs locally."""
    picked = [s for s in signals if s["kind"] in INSIGHT_KINDS][:3]
    return json.dumps({
        "priority_order": [{"task_id": t["id"], "reason": f"{t['priority'].capitalize()} priority."} for t in cands],
        "insights": [{"title": s["kind"].replace("_", " ").capitalize(), "explanation": s["text"],
                      "evidence": [s["id"]], "recommendation": "I'd recommend doing the tasks named here first."}
                     for s in picked],
        "watch": [],
    })


def _call_ai(prompt: str, signals: list, cands: list) -> str:
    from app.services.ai_model_service import ai_model_service
    if ai_model_service.fast_provider_name().startswith("Placeholder"):
        return _placeholder_answer(signals, cands)
    return ai_model_service.fast_complete_direct(prompt, max_tokens=MAX_TOKENS, timeout=TIMEOUT_S - 5,
                                                temperature=TEMPERATURE)


def _call_with_limit(prompt: str, signals: list, cands: list) -> tuple[str | None, str | None]:
    pool = ThreadPoolExecutor(max_workers=1)
    future = pool.submit(_call_ai, prompt, signals, cands)
    try:
        return future.result(timeout=TIMEOUT_S), None
    except _Timeout:
        return None, f"no answer within {TIMEOUT_S:.0f} s"
    except Exception as exc:
        return None, f"AI call failed: {exc}"
    finally:
        pool.shutdown(wait=False)


# ── Validation ─────────────────────────────────────────────────────────────────

def _rule_reason(t: dict, today, signals: list) -> str:
    when = "overdue" if t["due"] < today else sig.rel(t["due"], today)
    reason = f"{t['priority'].capitalize()} priority, due {when}"
    linked = next((s for s in signals if t["id"] in s["sources"]["tasks"] and s["kind"] in ("deadline", "dependency")
                   and s["sources"]["plan_events"]), None)
    if linked:
        e = linked["sources"]["plan_events"][0]
        reason += f" – before {sig.EVENT_VERB.get(e['event'], e['event'])} {e['crop']} {sig.fmt(date.fromisoformat(e['date']))}"
    return reason + "."


def validate(answer: dict, signals: list, cands: list, bare_fields: set, today) -> dict:
    by_id = {s["id"]: s for s in signals}
    cand_by_id = {t["id"]: t for t in cands}
    all_dates = {date.fromisoformat(d) for s in signals for d in s["dates"]} | {t["due"] for t in cands}
    dropped = []

    order, seen = [], set()
    for item in answer.get("priority_order") or []:
        try:
            tid = int(item.get("task_id"))
        except (TypeError, ValueError, AttributeError):
            dropped.append({"section": "priority_order", "item": item, "reason": "no task id"})
            continue
        if tid not in cand_by_id or tid in seen:
            dropped.append({"section": "priority_order", "item": item,
                            "reason": "duplicate" if tid in seen else "not a task due today/tomorrow"})
            continue
        t, reason = cand_by_id[tid], str(item.get("reason") or "").strip()
        problem = (val.style_problem(reason) or
                   ("date not in the data" if val.dates_outside(reason, all_dates) else None))
        if not reason or problem:
            if reason:
                dropped.append({"section": "priority_order", "item": item, "reason": f"reason replaced: {problem}"})
            reason, source = _rule_reason(t, today, signals), "rule"
        else:
            source = "ai"
        seen.add(tid)
        order.append({**_task_out(t), "reason": reason, "source": source})
    for t in cands:                                   # tasks the AI left out keep the rule order
        if t["id"] not in seen:
            order.append({**_task_out(t), "reason": _rule_reason(t, today, signals), "source": "rule"})

    def items(section, raw, limit, text_keys):
        out = []
        for item in raw or []:
            if not isinstance(item, dict):
                dropped.append({"section": section, "item": item, "reason": "not an object"})
                continue
            ev = val.evidence_ids(item.get("evidence"))
            texts = [str(item.get(k) or "") for k in text_keys]
            problem = val.check(texts, ev, by_id, bare_fields)
            if problem is None and not texts[0].strip():
                problem = "empty"
            if problem:
                dropped.append({"section": section, "item": item, "reason": problem})
                logger.info("Task insights: %s dropped (%s): %r", section, problem, item)
                continue
            if len(out) >= limit:
                dropped.append({"section": section, "item": item, "reason": f"more than {limit}"})
                continue
            out.append({**{k: str(item.get(k) or "").strip() for k in text_keys},
                        "evidence": ev, "based_on": val.based_on(ev, by_id)})
        return out

    return {
        "priority_order": order,
        "insights": items("insights", answer.get("insights"), MAX_INSIGHTS, ("title", "explanation", "recommendation")),
        "watch": items("watch", answer.get("watch"), MAX_WATCH, ("text",)),
        "dropped": dropped,
    }


def _task_out(t: dict) -> dict:
    return {"task_id": t["id"], "title": t["title"], "due": t["due"].isoformat(), "priority": t["priority"],
            "field": t["field"]}


# ── Basic summary (no AI) ──────────────────────────────────────────────────────

_KIND_TITLE = {"deadline": "Deadline", "dependency": "Before a plan event", "weather": "Weather window",
               "load": "Busy days", "plan_change": "Plan change"}


def basic_summary(signals: list, cands: list, today, error: str | None) -> dict:
    by_id = {s["id"]: s for s in signals}
    top = [s for s in signals if s["kind"] in INSIGHT_KINDS][:3]
    return {
        "priority_order": [{**_task_out(t), "reason": _rule_reason(t, today, signals), "source": "rule"}
                           for t in cands],
        "insights": [{"title": _KIND_TITLE.get(s["kind"], s["kind"]), "explanation": s["text"], "recommendation": "",
                      "evidence": [s["id"]], "based_on": val.based_on([s["id"]], by_id)} for s in top],
        "watch": [],
        "dropped": [],
    }


# ── Generate ───────────────────────────────────────────────────────────────────

def generate(user_id: int) -> dict:
    """One AI call → validated, stored task insights. Returns the stored payload."""
    from app.services.ai_model_service import ai_model_service
    today = clock.today()
    parts = reports.fingerprint_parts(user_id, today)       # the data this result is based on
    snapshot = sig.collect(user_id, today)
    signals = sig.build_from(snapshot)
    cands = candidates(snapshot)
    bare = {f["id"] for f in snapshot["fields"] if f["bare"]}

    prompt = build_prompt(signals, cands, today)
    t0 = time.monotonic()
    raw, error = _call_with_limit(prompt, signals, cands)
    latency_ms = round((time.monotonic() - t0) * 1000)
    answer = parse_json_object(raw) if raw else None
    if raw and answer is None:
        error = "answer is not JSON"
    elif not raw and not error:
        error = "empty answer"

    if answer is None:
        logger.warning("Task insights user=%s: basic summary (%s)", user_id, error)
        data, is_fallback = basic_summary(signals, cands, today, error), True
    else:
        data, is_fallback = validate(answer, signals, cands, bare, today), False
    data.update({"basic_summary": is_fallback, "error": error, "raw_answer": (raw or "")[:4000],
                 "prompt_chars": len(prompt)})
    try:
        model = ai_model_service.fast_provider_name()
    except Exception:
        model = None
    reports.save(user_id, KIND, data, signals, is_fallback=is_fallback, latency_ms=latency_ms, model=model,
                 parts=parts)
    logger.info("Task insights user=%s: %s, %d ms, %d insights, %d dropped", user_id,
                "basic summary" if is_fallback else "AI", latency_ms, len(data["insights"]), len(data["dropped"]))
    return reports.payload(user_id, KIND)
