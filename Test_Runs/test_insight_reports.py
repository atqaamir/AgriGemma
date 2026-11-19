"""Stored AI insight results + staleness (Step G.3) — no AI.

Run from the project root with DEMO_TODAY=2027-05-05 USE_PLACEHOLDER_AI=true:
    python Test_Runs/test_insight_reports.py
Reseeds the local DB (like a server start). Checks that a stored report is "unchanged"
until the tasks, the plan or the demo date change, and that reading never calls the AI.
"""
import json
import os
import sys
from datetime import timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FAILED = []


def check(cond, label):
    print(f"  {'OK  ' if cond else 'FAIL'} {label}")
    if not cond:
        FAILED.append(label)


from run import app  # noqa: E402  bootstrap(): fresh reseed

with app.app_context():
    from sqlalchemy import inspect
    from app.extensions import db
    from app.agents.coordinator_agent import CoordinatorAgent
    from app.models.task import Task
    from app.models.ai_insight_report import AiInsightReport
    from app.repositories.weekly_plan_repository import WeeklyPlanRepository
    from app.services import insight_report_service as reports
    from app.services import insight_signals_service as sig
    from app.services.ai_model_service import ai_model_service
    from app.utils import clock

    # Reading must never call the AI.
    calls = {"n": 0}
    for name in ("complete", "fast_complete", "fast_complete_json", "fast_complete_direct"):
        orig = getattr(ai_model_service, name, None)
        if orig:
            def wrapped(*a, _orig=orig, **k):
                calls["n"] += 1
                return _orig(*a, **k)
            setattr(ai_model_service, name, wrapped)

    uid, today = 1, clock.today()
    print(f"\n-- user {uid} on {today}")
    tables = set(inspect(db.engine).get_table_names())
    check({"ai_insight_report", "dashboard_summary", "task_intelligence_summary"} <= tables,
          "new table created; old dashboard_summary / task_intelligence_summary still there (no DROP)")
    check(AiInsightReport.query.count() == 0, "reseed leaves no reports")

    from app.services import demo_scenario_service
    demo_scenario_service.apply(1, "typical")   # scenario 1: 7–8 May western disturbance
    CoordinatorAgent().daily_update(user_id=uid, as_of_date=today)
    signals = sig.build_signals(uid)
    row = reports.save(uid, "task_insights", {"insights": []}, signals, is_fallback=True)
    calls["n"] = 0

    reads = {"ai_calls": 0}

    def stale(label, want_stale, want_changed=None):
        before = calls["n"]
        p = reports.payload(uid, "task_insights")
        reads["ai_calls"] += calls["n"] - before     # only calls made while reading
        ok = p["stale"] == want_stale and (want_changed is None or p["changed"] == want_changed)
        check(ok, f"{label}: stale={p['stale']} changed={p['changed']}"
                  + (f" banner={p['banner']!r}" if p["banner"] else ""))
        return p

    p = stale("just saved", False, [])
    check(p["data"] == {"insights": []} and len(p["signals"]) == len(signals), "payload returns data + signals")
    check(reports.payload(uid, "farm_report") is None, "kinds are separate (no farm report yet)")

    CoordinatorAgent().daily_update(user_id=uid, as_of_date=today)
    stale("same-day simulator rerun (same plan)", False, [])

    t = Task.query.filter_by(user_id=uid, task_category="plan", is_active=True).first()
    t.ai_explanation = "Filled in later by the explanation run."
    db.session.commit()
    stale("an AI explanation filled in", False, [])

    erosion = Task.query.filter(Task.user_id == uid, Task.title.like("%Erosion%")).first()
    erosion.due_date = erosion.due_date + timedelta(days=1)
    db.session.commit()
    stale("a task's due date moved", True, ["tasks"])
    erosion.due_date = erosion.due_date - timedelta(days=1)
    db.session.commit()
    stale("moved back", False, [])

    erosion.completed = True
    db.session.commit()
    stale("a task completed", True, ["tasks"])
    after_done = sig.build_signals(uid)
    diff = reports.what_changed(signals, after_done)
    check(any(c["before"]["kind"] == "dependency" for c in diff["changed"]) or
          any(s["kind"] == "dependency" for s in diff["removed"]),
          f"what_changed sees the dependency signal change "
          f"(added {len(diff['added'])}, removed {len(diff['removed'])}, changed {len(diff['changed'])})")
    erosion.completed = False
    db.session.commit()
    stale("un-completed", False, [])

    weekly = WeeklyPlanRepository.get_active_by_user_id(uid)
    entry = next(e for e in weekly.entries if json.loads(e.week_events or "[]"))
    saved_events = entry.week_events
    ev = json.loads(saved_events)
    ev[0]["date"] = (today + timedelta(days=3)).isoformat()
    entry.week_events = json.dumps(ev)
    db.session.commit()
    stale("a plan event moved", True, ["plan"])
    entry.week_events = saved_events
    db.session.commit()
    stale("plan restored", False, [])

    os.environ["DEMO_TODAY"] = (today + timedelta(days=1)).isoformat()
    stale("next demo day", True, ["date"])
    os.environ["DEMO_TODAY"] = today.isoformat()

    check(reports.what_changed(None, signals)["first_report"], "what_changed: no previous report → first report")
    check(reads["ai_calls"] == 0, f"no AI call while reading reports ({reads['ai_calls']}; "
                                  f"{calls['n']} from the simulator reruns' notifications)")

    reports.save(uid, "farm_report", {"headline": "x"}, signals, is_fallback=False, latency_ms=1234, model="test")
    fr = reports.payload(uid, "farm_report")
    check(fr["latency_ms"] == 1234 and fr["model"] == "test" and not fr["stale"], "farm report stored with latency/model")
    check(reports.latest(uid, "task_insights").id == row.id, "latest per kind")

    from Test_Runs.seed_data import clear_demo_tables
    clear_demo_tables()
    check(AiInsightReport.query.count() == 0, "clear_demo_tables empties ai_insight_report")

print(f"\n{'ALL PASSED' if not FAILED else f'{len(FAILED)} FAILED: {FAILED}'}")
sys.exit(1 if FAILED else 0)
