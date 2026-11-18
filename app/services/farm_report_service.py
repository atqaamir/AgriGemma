"""Farm report (dashboard): one AI call on "Generate report".

  signals (insight_signals_service) + season lines (planned vs actual per crop) + what changed
  since the previous farm report (diff of the stored signals, computed in code)
    → one fast_complete_direct call (minimal thinking, temperature 0.1, JSON parsed tolerantly)
    → validation: insights as on the tasks page (evidence ids, dates, style, bare fields, max 3);
      headline / sections with a date not in the data or banned phrasing are replaced by their
      rule-based text
    → stored in ai_insight_report (kind "farm_report").
No usable answer → the same report built from the rules, labelled "basic summary".

Output: {"headline", "sections": {farm_status, season_progress, what_changed, next_7_days},
         "section_source": {name: "ai"|"rule"}, "insights": [...], "changes": {...},
         "dropped": [...], "basic_summary": bool, "error"}
"""
from __future__ import annotations

import json
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as _Timeout
from datetime import date

from app.services import insight_report_service as reports
from app.services import insight_signals_service as sig
from app.services import insight_validation as val
from app.utils import clock
from app.utils.ai_json import parse_json_object
from app.utils.date_guard import dates_in, dates_outside

logger = logging.getLogger(__name__)

KIND = "farm_report"
MAX_INSIGHTS = 3
CALL_TIMEOUT_S = 25.0     # per model request: bigger prompt/answer than task insights
TIMEOUT_S = 55.0          # whole call: primary + fallback
MAX_TOKENS = 1500
TEMPERATURE = 0.1
SECTIONS = ("farm_status", "season_progress", "what_changed", "next_7_days")
SECTION_TITLES = {"farm_status": "Farm status", "season_progress": "Season progress",
                  "what_changed": "What changed", "next_7_days": "Next 7 days"}
MAX_CHANGES = 6

_SYSTEM = (
    "You write a short weekly farm report for the farmer, based only on the facts below: SIGNALS "
    "(worked out from the farm's plan, tasks, forecast and fields, each with an id like S3), SEASON "
    "(planned vs actual dates per crop) and CHANGES (what changed since the last report).\n"
    "Rules:\n"
    "1. Use only these facts. Connect them; add no facts, numbers, dates, causes or tasks that are not "
    "in them.\n"
    "2. headline: one sentence – the most important thing for the farm this week.\n"
    "3. sections, each 1–3 short sentences:\n"
    "   farm_status – the fields: sown or bare, their condition in words;\n"
    "   season_progress – planned vs actual per crop from SEASON, including crops that are Not Feasible;\n"
    "   what_changed – only from CHANGES (if it says this is the first report, say so);\n"
    "   next_7_days – risks and outlook from the deadline, dependency and weather signals.\n"
    "4. insights: at most 3, farm-level. If a crop is Not Feasible this season, one insight covers it "
    "(what it means for that field). The others cover the most urgent risks of the next 7 days "
    "(deadlines, dependencies, weather windows). Each cites at least one signal id in evidence and "
    "mentions only dates that appear in the signals it cites. If an insight names a date or a task from "
    "another signal, add that signal to its evidence too.\n"
    "5. Recommend, don't decide: never move dates, never create or cancel tasks, never say you changed "
    "something. Phrase recommendations as \"I'd recommend …\".\n"
    "6. Style: refer to tasks by their title. Never write \"I understand\", \"I know\", \"you must\" or "
    "\"must\". Describe scores and risks in words (low / moderate / high), not numbers. Where nothing is "
    "sown (bare field) there are no plants: do not mention leaves, stems or wilting there.\n"
    "Answer with compact JSON only (no code fence, no other text):\n"
    '{"headline": "...", "sections": {"farm_status": "...", "season_progress": "...", '
    '"what_changed": "...", "next_7_days": "..."}, "insights": [{"title": "max 8 words", '
    '"explanation": "1-2 sentences", "evidence": ["S8"], "recommendation": "I\'d recommend ..."}]}'
)


# ── Inputs ─────────────────────────────────────────────────────────────────────

def season_lines(snapshot: dict) -> list[str]:
    """Planned vs actual per crop of the seasonal plan."""
    lines = []
    for e in snapshot["entries"]:
        where = f" on {e['field']}" if e["field"] else ""
        if e["feasibility"] == "Not Feasible":
            lines.append(f"{e['crop']}{where}: Not Feasible this season – no dates planned.")
            continue
        planned, eff = e.get("planned") or {}, e.get("effective") or {}
        p_sow, a_sow = planned.get("sowing"), eff.get("sowing") or planned.get("sowing")
        if e["sowing_done_on"]:
            sow = f"sown on {sig.fmt(e['sowing_done_on'])} (planned {sig.fmt(p_sow)})"
        elif e["sowing_status"] in ("decision_needed", "overdue"):
            sow = f"sowing {e['sowing_status'].replace('_', ' ')} (planned {sig.fmt(p_sow)})"
        elif p_sow and a_sow and a_sow != p_sow:
            sow = f"not sown yet; sowing planned {sig.fmt(p_sow)}, now {sig.fmt(a_sow)}"
        else:
            sow = f"not sown yet; sowing planned {sig.fmt(p_sow)}"
        harvest = eff.get("harvesting") or planned.get("harvesting")
        lines.append(f"{e['crop']}{where}: {sow}; harvest {sig.fmt(harvest)}.")
    return lines


def change_lines(previous: dict | None, signals: list) -> tuple[list[str], dict]:
    """What changed since the previous farm report, in plain lines (computed in code)."""
    if previous is None:
        return ["This is the first farm report."], {"first_report": True}
    diff = reports.what_changed(previous["signals"], signals)
    since = sig.fmt(date.fromisoformat(previous["as_of_date"]))
    lines = []
    for s in diff["added"]:
        lines.append(f"New since {since}: {s['text']}")
    for s in diff["removed"]:
        lines.append(f"No longer the case: {s['text']}")
    for c in diff["changed"]:
        if c["after"]["kind"] in ("field_status", "load"):
            continue
        lines.append(f"Changed: {c['after']['text']}")
    if not lines:
        lines = [f"Nothing changed since the last report ({since})."]
    return lines[:MAX_CHANGES], {"first_report": False, "since": previous["as_of_date"],
                                 "added": len(diff["added"]), "removed": len(diff["removed"]),
                                 "changed": len(diff["changed"])}


def build_prompt(signals: list, season: list, changes: list, today) -> str:
    from app.services.intelligence_service.chatbot_service.prompts._prompt_chatbot_service import _SYSTEM_SEP
    day = f"{today.strftime('%A')} {today.day} {today.strftime('%B %Y')}"
    return (f"{_SYSTEM}{_SYSTEM_SEP}TODAY: {day}\n\nSIGNALS:\n{sig.prompt_lines(signals)}\n\n"
            + "SEASON:\n" + "\n".join(f"- {x}" for x in season) + "\n\n"
            + "CHANGES:\n" + "\n".join(f"- {x}" for x in changes))


# ── Rule-based report (basic summary + per-section fallback) ───────────────────

def _first_sentence(text: str) -> str:
    m = re.match(r"(.+?[.!?])(\s|$)", text or "")
    return m.group(1) if m else (text or "")


def rule_report(signals: list, season: list, changes: list) -> dict:
    by_kind = lambda *kinds: [s for s in signals if s["kind"] in kinds]
    fields = by_kind("field_status")
    nxt = by_kind("deadline", "dependency", "weather")[:3]
    top = signals[0] if signals else None
    return {
        "headline": _first_sentence(top["text"]) if top else "Nothing urgent on the farm this week.",
        "sections": {
            "farm_status": " ".join(_first_sentence(s["text"]) if len(s["text"]) > 160 else s["text"]
                                    for s in fields) or "No active fields.",
            "season_progress": " ".join(season) or "No seasonal plan.",
            "what_changed": " ".join(changes),
            "next_7_days": " ".join(_first_sentence(s["text"]) for s in nxt) or "No deadlines or weather risks "
                                                                                 "in the next 7 days.",
        },
    }


def _rule_insights(signals: list) -> list:
    by_id = {s["id"]: s for s in signals}
    nf = [s for s in signals if s["key"].startswith("plan:not_feasible")][:1]
    rest = [s for s in signals if s["kind"] in ("deadline", "dependency", "weather")][:MAX_INSIGHTS - len(nf)]
    titles = {"deadline": "Deadline", "dependency": "Before a plan event", "weather": "Weather window",
              "plan_change": "Plan change"}
    return [{"title": titles.get(s["kind"], s["kind"]), "explanation": s["text"], "recommendation": "",
             "evidence": [s["id"]], "based_on": val.based_on([s["id"]], by_id)} for s in rest + nf]


def basic_summary(signals: list, season: list, changes: list) -> dict:
    r = rule_report(signals, season, changes)
    return {**r, "section_source": {k: "rule" for k in SECTIONS}, "insights": _rule_insights(signals),
            "dropped": []}


# ── Validation ─────────────────────────────────────────────────────────────────

def validate(answer: dict, signals: list, season: list, changes: list, bare_fields: set,
             all_bare: bool) -> dict:
    by_id = {s["id"]: s for s in signals}
    year = clock.today().year
    known = {date.fromisoformat(d) for s in signals for d in s["dates"]}
    for line in season + changes:
        known |= {date(year, m, d) for d, m in dates_in(line) if not (m == 2 and d == 29)}
    rule = rule_report(signals, season, changes)
    dropped = []

    def text_ok(text: str) -> str | None:
        if not text.strip():
            return "empty"
        outside = dates_outside(text, known)
        if outside:
            return "date not in the data: " + ", ".join(f"{d}/{m}" for d, m in outside)
        problem = val.style_problem(text)
        if problem:
            return f"style: {problem}"
        if all_bare and val._PLANT.search(text):
            return "plant terms (leaves/stems) while nothing is sown"
        return None

    headline = str(answer.get("headline") or "").strip()
    problem = text_ok(headline)
    if problem:
        dropped.append({"section": "headline", "item": headline, "reason": problem})
        headline = rule["headline"]

    sections, source = {}, {}
    raw_sections = answer.get("sections") if isinstance(answer.get("sections"), dict) else {}
    for name in SECTIONS:
        text = str(raw_sections.get(name) or "").strip()
        problem = text_ok(text)
        if problem:
            if text:
                dropped.append({"section": name, "item": text, "reason": problem})
            sections[name], source[name] = rule["sections"][name], "rule"
        else:
            sections[name], source[name] = text, "ai"

    insights = []
    for item in answer.get("insights") or []:
        if not isinstance(item, dict):
            dropped.append({"section": "insights", "item": item, "reason": "not an object"})
            continue
        ev = val.evidence_ids(item.get("evidence"))
        texts = [str(item.get(k) or "") for k in ("title", "explanation", "recommendation")]
        problem = val.check(texts, ev, by_id, bare_fields) or (None if texts[0].strip() else "empty")
        if not problem and len(insights) >= MAX_INSIGHTS:
            problem = f"more than {MAX_INSIGHTS}"
        if problem:
            dropped.append({"section": "insights", "item": item, "reason": problem})
            logger.info("Farm report: insight dropped (%s): %r", problem, item)
            continue
        insights.append({"title": texts[0].strip(), "explanation": texts[1].strip(),
                         "recommendation": texts[2].strip(), "evidence": ev, "based_on": val.based_on(ev, by_id)})
    return {"headline": headline, "sections": sections, "section_source": source, "insights": insights,
            "dropped": dropped}


# ── AI call (replaced in tests) ────────────────────────────────────────────────

def _placeholder_answer(signals: list, season: list, changes: list) -> str:
    r = rule_report(signals, season, changes)
    ins = [{k: v for k, v in i.items() if k != "based_on"} for i in _rule_insights(signals)]
    for i in ins:
        i["recommendation"] = "I'd recommend planning the week around this."
    return json.dumps({**r, "insights": ins})


def _call_ai(prompt: str, signals: list, season: list, changes: list) -> str:
    from app.services.ai_model_service import ai_model_service
    if ai_model_service.fast_provider_name().startswith("Placeholder"):
        return _placeholder_answer(signals, season, changes)
    return ai_model_service.fast_complete_direct(prompt, max_tokens=MAX_TOKENS, timeout=CALL_TIMEOUT_S,
                                                temperature=TEMPERATURE)


def _call_and_model(*args):
    """_call_ai plus the model that answered (read in the same thread as the call)."""
    from app.services.ai_model_service import ai_model_service
    text = _call_ai(*args)
    return text, ai_model_service.answered_model()


def _call_with_limit(*args) -> tuple[str | None, str | None, str | None]:
    pool = ThreadPoolExecutor(max_workers=1)
    future = pool.submit(_call_and_model, *args)
    try:
        raw, answered = future.result(timeout=TIMEOUT_S)
        return raw, None, answered
    except _Timeout as exc:
        if future.done():   # the provider's own HTTP timeout (also a TimeoutError), not our limit
            return None, f"AI provider timed out ({exc or 'no response'})", None
        return None, f"no answer within {TIMEOUT_S:.0f} s", None
    except Exception as exc:
        return None, f"AI call failed: {exc}", None
    finally:
        pool.shutdown(wait=False)


# ── Generate ───────────────────────────────────────────────────────────────────

def generate(user_id: int) -> dict:
    """One AI call → validated, stored farm report. Returns the stored payload."""
    from app.services.ai_model_service import ai_model_service
    today = clock.today()
    parts = reports.fingerprint_parts(user_id, today)
    snapshot = sig.collect(user_id, today)
    signals = sig.build_from(snapshot)
    season = season_lines(snapshot)
    previous = reports.payload(user_id, KIND)
    changes, change_info = change_lines(previous, signals)
    bare = {f["id"] for f in snapshot["fields"] if f["bare"]}
    all_bare = bool(snapshot["fields"]) and all(f["bare"] for f in snapshot["fields"])

    prompt = build_prompt(signals, season, changes, today)
    t0 = time.monotonic()
    raw, error, answered = _call_with_limit(prompt, signals, season, changes)
    latency_ms = round((time.monotonic() - t0) * 1000)
    answer = parse_json_object(raw) if raw else None
    if raw and answer is None:
        error = "answer is not JSON"
    elif not raw and not error:
        error = "empty answer"

    if answer is None:
        logger.warning("Farm report user=%s: basic summary (%s)", user_id, error)
        data, is_fallback = basic_summary(signals, season, changes), True
    else:
        data, is_fallback = validate(answer, signals, season, changes, bare, all_bare), False
    data.update({"changes": {**change_info, "lines": changes}, "season": season, "basic_summary": is_fallback,
                 "error": error, "raw_answer": (raw or "")[:4000], "prompt_chars": len(prompt)})
    try:
        model = ai_model_service.fast_provider_name()
        if answered and answered not in model:          # the fallback model answered
            model = f"{model.split('/')[0]}/{answered} (fallback)"
    except Exception:
        model = None
    reports.save(user_id, KIND, data, signals, is_fallback=is_fallback, latency_ms=latency_ms, model=model,
                 parts=parts)
    logger.info("Farm report user=%s: %s, %d ms, %d insights, %d dropped", user_id,
                "basic summary" if is_fallback else "AI", latency_ms, len(data["insights"]), len(data["dropped"]))
    return reports.payload(user_id, KIND)
