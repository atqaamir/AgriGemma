"""Farm report (Step G.4): parse → validate → store, with the placeholder and made-up answers.

Run from the project root with DEMO_TODAY=2027-05-05 USE_PLACEHOLDER_AI=true:
    python Test_Runs/test_farm_report.py
Reseeds the local DB, runs the simulator's daily update for 5 May 2027.
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


from run import app  # noqa: E402  bootstrap(): fresh reseed

with app.app_context():
    from app.extensions import db
    from app.agents.coordinator_agent import CoordinatorAgent
    from app.models.task import Task
    from app.services import farm_report_service as fr
    from app.services import insight_report_service as reports
    from app.services import insight_signals_service as sig
    from app.utils import clock

    today = clock.today()
    CoordinatorAgent().daily_update(user_id=1, as_of_date=today)
    signals = sig.build_signals(1)
    nf = next(s["id"] for s in signals if s["key"].startswith("plan:not_feasible"))
    rain = next(s["id"] for s in signals if s["key"].startswith("weather:rain"))

    def run_with(answer):
        orig = fr._call_ai

        def fake(*args):
            if isinstance(answer, Exception):
                raise answer
            return answer
        fr._call_ai = fake
        try:
            return fr.generate(1)
        finally:
            fr._call_ai = orig

    print(f"\n-- placeholder report, user 1 on {today}")
    p = fr.generate(1)
    d = p["data"]
    check(not p["is_fallback"] and d["headline"] and all(d["sections"][k] for k in fr.SECTIONS),
          f"headline + 4 sections: {d['headline'][:80]!r}")
    check(any(nf in i["evidence"] for i in d["insights"]) and len(d["insights"]) <= 3,
          f"Rice Not Feasible insight ({nf}) among ≤ 3 insights")
    check(d["changes"]["first_report"] and "first farm report" in d["sections"]["what_changed"],
          "first report says so in 'what changed'")
    check(any("Rice" in x and "Not Feasible" in x for x in d["season"]) and
          any("Cotton" in x and "now 9 May" in x for x in d["season"]), "season lines: Rice Not Feasible, cotton 7 → 9 May")
    check(not p["stale"], "no 'changed' banner right after generating")

    p2 = fr.generate(1)
    check(p2["data"]["changes"]["lines"][0].startswith("Nothing changed"), "same data → 'Nothing changed since…'")

    erosion = Task.query.filter(Task.user_id == 1, Task.title.like("%Erosion%")).first()
    erosion.completed = True
    db.session.commit()
    check(reports.payload(1, "farm_report")["stale"], "task completed → banner (no AI call)")
    p3 = fr.generate(1)
    lines = p3["data"]["changes"]["lines"]
    check(not p3["stale"] and any("Erosion" in x for x in json.loads(json.dumps(
        [s["text"] for s in reports.what_changed(p2["signals"], p3["signals"])["removed"]] +
        [c["before"]["text"] for c in reports.what_changed(p2["signals"], p3["signals"])["changed"]]))),
          f"regenerated: what changed sees the erosion task ({len(lines)} lines)")
    erosion.completed = False
    db.session.commit()

    print("\n-- validation (made-up answers)")
    answer = {
        "headline": "Showers on 7–8 May come before the cotton sowing on 9 May.",
        "sections": {"farm_status": "All three fields are bare.", "season_progress": "Maize is sown on 1 May.",
                     "what_changed": "You must regenerate.", "next_7_days": "Showers on 7–8 May."},
        "insights": [
            {"title": "Rice not feasible", "explanation": "Rice cannot grow on North Field Alpha this season.",
             "evidence": [nf], "recommendation": "I'd recommend choosing a different crop for this field."},
            {"title": "Bad id", "explanation": "x", "evidence": ["S77"], "recommendation": ""},
            {"title": "Wrong date", "explanation": "Showers on 7–8 May, so sow on 15 May.", "evidence": [rain],
             "recommendation": ""},
            {"title": "Leaves", "explanation": "The rice leaves look yellow.", "evidence": [nf], "recommendation": ""},
        ],
    }
    p = run_with("Here is the report:\n```json\n" + json.dumps(answer) + "\n```")
    d = p["data"]
    src = d["section_source"]
    check(d["headline"] == answer["headline"], "valid headline kept")
    check(src["season_progress"] == "rule" and src["what_changed"] == "rule"
          and src["farm_status"] == "ai" and src["next_7_days"] == "ai",
          f"sections with a date not in the data / 'you must' → rule text ({src})")
    check([i["title"] for i in d["insights"]] == ["Rice not feasible"], "only the valid insight is shown")
    reasons = {x["item"].get("title"): x["reason"] for x in d["dropped"] if isinstance(x["item"], dict)}
    check(reasons.get("Bad id", "").startswith("unknown evidence") and
          reasons.get("Wrong date", "").startswith("date not in its evidence") and
          "bare field" in reasons.get("Leaves", ""), f"dropped: {reasons}")
    check(d["insights"][0]["based_on"] == ["Rice not feasible"], f"based on: {d['insights'][0]['based_on']}")

    print("\n-- basic summary (no AI result)")
    for label, ans in [("AI failure", RuntimeError("HTTP 503")), ("not JSON", "Sorry, no.")]:
        p = run_with(ans)
        d = p["data"]
        check(p["is_fallback"] and d["headline"] and all(d["sections"][k] for k in fr.SECTIONS)
              and any(nf in i["evidence"] for i in d["insights"]),
              f"{label} → basic summary with all sections and the Rice insight (error {d['error']!r})")

    print("\n-- dashboard JSON")
    from app.services.dashboard_service import DashboardService
    dash = DashboardService.build_dashboard_data(1)
    check("dashboard_summary" not in dash and dash["farm_report"]["id"] == p["id"] and not dash["farm_report"]["stale"],
          "dashboard carries the latest farm report, unchanged → no banner")

print(f"\n{'ALL PASSED' if not FAILED else f'{len(FAILED)} FAILED: {FAILED}'}")
sys.exit(1 if FAILED else 0)
