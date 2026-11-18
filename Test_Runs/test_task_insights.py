"""Task insights (Step G.5): parse → validate → store, with made-up AI answers. No real AI.

Run from the project root with DEMO_TODAY=2027-05-05 USE_PLACEHOLDER_AI=true:
    python Test_Runs/test_task_insights.py
Reseeds the local DB, runs the simulator's daily update for 5 May 2027, then replaces the AI
call with fixed answers (fenced JSON, chatty prefix, invalid evidence, wrong dates, style
problems, unknown task ids, failure / timeout / no JSON) and checks what is shown.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FAILED = []


def check(cond, label):
    print(f"  {'OK  ' if cond else 'FAIL'} {label}")
    if not cond:
        FAILED.append(label)


from app.utils.ai_json import parse_json_object  # noqa: E402

print("\n-- tolerant JSON parse")
obj = {"a": 1, "b": "x } y", "c": [1, {"d": 2}]}
check(parse_json_object("```json\n" + json.dumps(obj, indent=2) + "\n```") == obj, "fenced ```json … ```")
check(parse_json_object("Sure! Here are the insights you asked for:\n" + json.dumps(obj) + "\nHope this helps.") == obj,
      "chatty prefix + trailing text")
check(parse_json_object('Note {not json} then ' + json.dumps(obj)) == obj, "skips a broken {…} before the object")
check(parse_json_object("no json here") is None and parse_json_object("") is None, "no object → None")

from run import app  # noqa: E402  bootstrap(): fresh reseed

with app.app_context():
    from app.agents.coordinator_agent import CoordinatorAgent
    from app.services import task_insights_service as ti
    from app.services import insight_signals_service as sig
    from app.utils import clock

    today = clock.today()
    CoordinatorAgent().daily_update(user_id=1, as_of_date=today)
    snap = sig.collect(1, today)
    signals = sig.build_from(snap)
    cands = ti.candidates(snap)
    by_kind = {s["kind"]: s for s in reversed(signals)}
    S = lambda kind: by_kind[kind]["id"]
    dep, rain, dl = S("dependency"), by_kind["weather"]["id"], S("deadline")
    erosion = next(t["id"] for t in cands if "Erosion" in t["title"])
    print(f"\n-- user 1 on {today}: {len(signals)} signals, {len(cands)} tasks today/tomorrow; "
          f"deadline {dl}, dependency {dep}, showers {rain}")

    def run_with(answer):
        """generate() with the AI call replaced by a fixed answer (str) or exception."""
        orig = ti._call_ai

        def fake(prompt, signals, cands):
            if isinstance(answer, Exception):
                raise answer
            return answer
        ti._call_ai = fake
        try:
            return ti.generate(1)
        finally:
            ti._call_ai = orig

    good = {
        "priority_order": [{"task_id": erosion, "reason": "Before the cotton sowing on 9 May."}],
        "insights": [
            {"title": "Erosion before cotton", "explanation": "The erosion work on The Reservoir comes before the "
             "cotton sowing on 9 May.", "evidence": [dep], "recommendation": "I'd recommend finishing it today."},
            {"title": "No evidence", "explanation": "Something.", "evidence": [], "recommendation": "x"},
            {"title": "Unknown id", "explanation": "Something.", "evidence": ["S99"], "recommendation": "x"},
            {"title": "Wrong date", "explanation": "Showers on 7–8 May, so sow cotton on 12 May.",
             "evidence": [rain], "recommendation": "x"},
            {"title": "Bossy", "explanation": "You must finish the seedbed.", "evidence": [dl], "recommendation": ""},
            {"title": "Decides", "explanation": "I've moved the sowing.", "evidence": [dl], "recommendation": ""},
            {"title": "Plants on bare field", "explanation": "The maize leaves will wilt.", "evidence": [dl],
             "recommendation": ""},
        ],
        "watch": [{"text": "Showers on 7–8 May.", "evidence": [rain]}, {"text": "No evidence here."}],
    }

    print("\n-- validation (fenced answer)")
    p = run_with("```json\n" + json.dumps(good, indent=2) + "\n```")
    d = p["data"]
    reasons = {x["item"].get("title") if isinstance(x["item"], dict) else None: x["reason"] for x in d["dropped"]}
    check(not p["is_fallback"] and [i["title"] for i in d["insights"]] == ["Erosion before cotton"],
          f"only the valid insight is shown: {[i['title'] for i in d['insights']]}")
    check(reasons.get("No evidence") == "no evidence", "no evidence → dropped")
    check(reasons.get("Unknown id", "").startswith("unknown evidence S99"), "unknown evidence id → dropped")
    check(reasons.get("Wrong date", "").startswith("date not in its evidence: 12/5"), "date not in evidence → dropped")
    check("you must" in reasons.get("Bossy", ""), "'you must' → dropped")
    check("decides" in reasons.get("Decides", ""), "'I've moved…' → dropped")
    check("bare field" in reasons.get("Plants on bare field", ""), "leaves/wilt on a bare field → dropped")
    check([w["text"] for w in d["watch"]] == ["Showers on 7–8 May."], "watch without evidence dropped")
    check(d["insights"][0]["based_on"][:1] == ["Sow Cotton 9 May"], f"based on: {d['insights'][0]['based_on']}")
    ids = [x["task_id"] for x in d["priority_order"]]
    check(ids[0] == erosion and sorted(ids) == sorted(t["id"] for t in cands),
          "priority order: AI's first, the tasks it left out follow in rule order, nothing else")
    check(all(x["source"] == "rule" for x in d["priority_order"][1:]), "left-out tasks get a rule reason")

    print("\n-- priority order limited to real task ids")
    bad_order = {"priority_order": [{"task_id": 99999, "reason": "x"}, {"task_id": erosion, "reason": "Today."},
                                    {"task_id": erosion, "reason": "again"}, {"task_id": "abc"}],
                 "insights": [], "watch": []}
    d = run_with("Sure, here you go: " + json.dumps(bad_order))["data"]
    ids = [x["task_id"] for x in d["priority_order"]]
    check(99999 not in ids and ids.count(erosion) == 1 and len(ids) == len(cands),
          f"unknown id, duplicate and non-number dropped ({len(d['dropped'])} dropped)")
    date_reason = {"priority_order": [{"task_id": erosion, "reason": "Before the showers on 20 May."}],
                   "insights": [], "watch": []}
    d = run_with(json.dumps(date_reason))["data"]
    check(d["priority_order"][0]["source"] == "rule", "reason with a date not in the data → rule reason")

    print("\n-- basic summary (no AI result)")
    for label, answer in [("AI failure", RuntimeError("HTTP 503")), ("not JSON", "I cannot help with that."),
                          ("empty", "")]:
        p = run_with(answer)
        d = p["data"]
        check(p["is_fallback"] and d["basic_summary"] and d["insights"] and len(d["priority_order"]) == len(cands),
              f"{label} → basic summary ({len(d['insights'])} signal cards, {len(d['priority_order'])} tasks, "
              f"error {d['error']!r})")
        check(all(i["evidence"] and i["based_on"] for i in d["insights"]), f"{label}: cards keep their evidence")

    print("\n-- placeholder provider end to end")
    p = ti.generate(1)
    check(not p["is_fallback"] and p["data"]["insights"] and not p["stale"], "placeholder answer validates and stores")

print(f"\n{'ALL PASSED' if not FAILED else f'{len(FAILED)} FAILED: {FAILED}'}")
sys.exit(1 if FAILED else 0)
