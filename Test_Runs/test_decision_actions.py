"""Decision needed (stage 2): "Sow anyway" and "Skip this season" on the decision task, and
undo from the weekly plan page – no AI, placeholder provider (the recommendation is set
directly where "against the recommendation" is checked).

Run from the project root with DEMO_TODAY=2027-05-05 USE_PLACEHOLDER_AI=true:
    python Test_Runs/test_decision_actions.py
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


from run import app  # noqa: E402

with app.app_context():
    from app.agents.coordinator_agent import CoordinatorAgent
    from app.extensions import db
    from app.models.plan_event_override import PlanEventOverride
    from app.models.seasonal_plan import SeasonalPlan
    from app.models.task import Task
    from app.services import deferred_ai_service as deferred
    from app.services import demo_scenario_service as scenarios
    from app.services.demo_reset_service import reset_demo
    from app.services.domain_service.task_service import TaskService
    from app.services.weekly_planning_service.weekly_planner_service import WeeklyPlannerService
    from app.utils import clock, demo_flags

    demo_flags.simulator_wait_seconds = lambda uid: 0
    client = app.test_client()
    today = clock.today()
    tomorrow = today + timedelta(days=1)
    first_ok = today + timedelta(days=4)          # 9 May: the first suitable day in scenario 3
    S3 = scenarios.WINDOW_RUNNING_OUT
    REC_SKIP = ("Skip the season. The sowing window ends on 8 May and every day left in it is unsuitable. "
                "The first suitable day, 9 May, is after the window.")

    def cotton_entry():
        db.session.expire_all()
        plan = SeasonalPlan.query.filter_by(user_id=1, currently_active=True).first()
        return next(e for e in plan.entries if e.crop_name_rel.name == "Cotton")

    def cotton_plan():
        return {x["crop_name"]: x for x in WeeklyPlannerService.show_active_plan(1)["entries"]}["Cotton"]

    def sowing_days():
        return [x["date"] for x in cotton_plan()["week_events"] if x["event_type"] == "sowing"]

    def decision_task():
        db.session.expire_all()
        return Task.query.filter_by(user_id=1, task_type="decision").order_by(Task.id.desc()).first()

    def cotton_tasks():
        db.session.expire_all()
        return Task.query.filter(Task.user_id == 1, Task.seasonal_plan_entry_id == cotton_entry().id,
                                 Task.task_type != "decision", Task.is_active.is_(True),
                                 Task.completed.is_(False)).all()

    def sow_cotton():
        return [t for t in cotton_tasks() if t.task_type == "planting"]

    def post(path):
        r = client.post(path)
        deferred.wait(1, 30)
        return r

    def start_s3():
        reset_demo()
        client.post("/mytasks/1/run-weather-simulator", json={"scenario": S3})
        deferred.wait(1, 30)
        d = decision_task()
        assert d is not None and d.is_active and not d.completed, "scenario 3 should open a decision task"
        return d

    # ── 1. Sow anyway (against the recommendation) ──────────────────────────────────────
    print("\n-- Sow anyway, against a 'skip the season' recommendation")
    d = start_s3()
    d.ai_explanation = REC_SKIP
    db.session.commit()
    r = post(f"/mytasks/1/decision/{d.id}/sow-anyway")
    body = r.get_json() or {}
    check(r.status_code == 200 and body.get("date") == first_ok.isoformat() and body.get("first_suitable") is True,
          f"HTTP {r.status_code}: the first suitable day {body}")
    check(body.get("against_recommendation") is True, "reported as against the recommendation")
    d = decision_task()
    hist = json.loads(d.task_changes or "[]")
    check(d.completed and hist[-1]["reason"] == "Decided: sow anyway on 9 May", "decision task closed (completed)")
    check(cotton_plan()["sowing_status"] == "farmer_planned" and sowing_days() == ["2027-05-09"],
          f"weekly plan: cotton sowing 9 May by the farmer ({cotton_plan()['sowing_status']}, {sowing_days()})")
    sow = sow_cotton()
    check(len(sow) == 1 and sow[0].due_date == first_ok and sow[0].task_category == "plan",
          f"Sow Cotton plan task due 9 May ({[(t.title, t.due_date) for t in sow]})")
    check(sow and "against the AI recommendation (skip the season)" in (sow[0].notes or ""),
          f"note: against the recommendation ({sow[0].notes if sow else None!r})")
    rows = PlanEventOverride.query.filter_by(seasonal_plan_entry_id=cotton_entry().id, source="farmer_planned").all()
    check(sorted(r.event_type for r in rows) == ["fertilization", "harvesting", "irrigation_start", "sowing"],
          f"farmer_planned overrides: sowing + cascades {sorted(r.event_type for r in rows)}")
    harvest = next(r for r in rows if r.event_type == "harvesting")
    check(harvest.actual_date.isoformat() == "2027-10-09", f"harvest moves with it (24 Sep → {harvest.actual_date})")

    print("   … the daily re-plan does not move it (the forecast still has no suitable day before 9 May)")
    CoordinatorAgent().daily_update(user_id=1, as_of_date=today, defer_ai=True)
    check(sowing_days() == ["2027-05-09"] and cotton_plan()["sowing_status"] == "farmer_planned",
          f"still 9 May after the daily update {sowing_days()}")
    check(not decision_task().is_active or decision_task().completed, "no decision task reopened")
    check(len(sow_cotton()) == 1, "still one Sow Cotton task")

    print("   … completing the Sow task records the sowing date as usual")
    sow_id = sow_cotton()[0].id
    TaskService.update_task(sow_id, {"completed": True})
    CoordinatorAgent().daily_update(user_id=1, as_of_date=today, defer_ai=True)
    check(cotton_plan()["sowing_status"] == "done", f"weekly plan: sowing done ({cotton_plan()['sowing_status']})")
    done = PlanEventOverride.query.filter_by(seasonal_plan_entry_id=cotton_entry().id, source="farmer_completed",
                                             event_type="sowing").first()
    check(done is not None and done.actual_date == today, f"farmer_completed sowing on {done and done.actual_date}")
    r = post(f"/mytasks/1/seasonal-entry/{cotton_entry().id}/undo-decision")
    check(r.status_code == 409, f"undo refused once sowing is recorded ({r.status_code} {r.get_json()})")

    # ── 2. Sow anyway (as recommended) + undo ───────────────────────────────────────────
    print("\n-- Sow anyway without a recommendation, then undo from the plan page")
    d = start_s3()
    r = post(f"/mytasks/1/decision/{d.id}/sow-anyway")
    check(r.status_code == 200 and r.get_json().get("against_recommendation") is False,
          "no recommendation: not 'against'")
    sow = sow_cotton()
    check(sow and "against" not in (sow[0].notes or ""), "note without 'against'")
    entry_id = cotton_entry().id
    r = post(f"/mytasks/1/seasonal-entry/{entry_id}/undo-decision")
    body = r.get_json() or {}
    check(r.status_code == 200 and body.get("undone") == "sow anyway", f"undo HTTP {r.status_code} {body}")
    check(not PlanEventOverride.query.filter_by(seasonal_plan_entry_id=entry_id, source="farmer_planned").count(),
          "farmer_planned overrides removed")
    check(cotton_plan()["sowing_status"] == "decision_needed" and sowing_days() == [],
          f"back to decision needed ({cotton_plan()['sowing_status']})")
    d = decision_task()
    check(d.is_active and not d.completed and d.due_date == today and "Decision undone (sow anyway)"
          in json.loads(d.task_changes)[-1]["reason"], "decision task reopened, due today")
    check(not sow_cotton(), "Sow Cotton deactivated again")
    check(len(Task.query.filter_by(user_id=1, task_type="decision").all()) == 1, "no duplicate decision task")

    # ── 3. Skip this season + undo ──────────────────────────────────────────────────────
    print("\n-- Skip this season, then undo from the plan page")
    r = post(f"/mytasks/1/decision/{d.id}/skip-season")
    check(r.status_code == 200 and (r.get_json() or {}).get("decision") == "skip_season", f"skip HTTP {r.status_code}")
    check(cotton_entry().skipped_on == today, "seasonal entry skipped_on = today")
    p = cotton_plan()
    check(p["sowing_status"] == "skipped" and p["week_events"] == [] and p["skipped_on"] == today.isoformat(),
          f"weekly plan: skipped, no events ({p['sowing_status']}, {p['week_events']})")
    check(not cotton_tasks(), f"no open cotton plan tasks {[t.title for t in cotton_tasks()]}")
    d = decision_task()
    check(d.completed and json.loads(d.task_changes)[-1]["reason"] == "Decided: skip this season",
          "decision task closed (completed)")
    CoordinatorAgent().daily_update(user_id=1, as_of_date=today, defer_ai=True)
    check(cotton_plan()["sowing_status"] == "skipped" and not cotton_tasks() and decision_task().completed,
          "still skipped after the daily update (no events, tasks or decision)")
    html = client.get("/1/weekly-plan-page").get_data(as_text=True)
    check("Skipped by the farmer" in html or '"skipped_on"' in html, "plan page has the skipped state")
    r = post(f"/mytasks/1/seasonal-entry/{cotton_entry().id}/undo-decision")
    check(r.status_code == 200 and (r.get_json() or {}).get("undone") == "skip this season", f"undo HTTP {r.status_code}")
    check(cotton_entry().skipped_on is None and cotton_plan()["sowing_status"] == "decision_needed",
          "undo: not skipped, decision needed again")
    d = decision_task()
    check(d.is_active and not d.completed, "decision task reopened")
    r = post(f"/mytasks/1/seasonal-entry/{cotton_entry().id}/undo-decision")
    check(r.status_code == 409, f"nothing left to undo → 409 ({r.status_code})")

    # ── 4. refused / cleared ────────────────────────────────────────────────────────────
    print("\n-- refused actions; another scenario / reset clears the decision")
    sow_task_any = Task.query.filter(Task.user_id == 1, Task.task_type == "planting").first()
    r = post(f"/mytasks/1/decision/{sow_task_any.id}/sow-anyway")
    check(r.status_code == 409, f"not a decision task → 409 ({r.status_code})")
    r = post(f"/mytasks/1/decision/{d.id}/skip-season")
    r2 = post(f"/mytasks/1/decision/{d.id}/sow-anyway")
    check(r.status_code == 200 and r2.status_code == 409, f"second answer to a closed decision → 409 ({r2.status_code})")
    client.post("/mytasks/1/run-weather-simulator", json={"scenario": "typical"})
    deferred.wait(1, 30)
    check(cotton_entry().skipped_on is None and cotton_entry().sowing == "05/07/2027",
          "scenario 1 after a skip: the simulated plan and its decision are gone (cotton 7 May)")
    check(sowing_days() == ["2027-05-09"], f"scenario 1 result unchanged (9 May) {sowing_days()}")
    start_s3()
    d = decision_task()
    post(f"/mytasks/1/decision/{d.id}/sow-anyway")
    reset_demo()
    check(not PlanEventOverride.query.filter_by(source="farmer_planned").count() and cotton_entry().skipped_on is None
          and cotton_entry().sowing == "05/07/2027", "Reset demo: no farmer decision, cotton 7 May")

print(f"\n{'ALL PASSED' if not FAILED else f'{len(FAILED)} FAILED: {FAILED}'}")
sys.exit(1 if FAILED else 0)
