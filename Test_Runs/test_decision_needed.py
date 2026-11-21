"""Decision needed (stage 1): scenario 3 "Sowing window running out", the "Decide: <crop> sowing"
task, the AI recommendation (fallback + guard) – no AI, placeholder provider (the AI call is
replaced by fixed answers where a recommendation is checked).

Run from the project root with DEMO_TODAY=2027-05-05 USE_PLACEHOLDER_AI=true:
    python Test_Runs/test_decision_needed.py
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

LIVE_TEXT = ("The sowing window ends on 8 May, and all remaining days within this period are unsuitable for "
             "sowing. Switching to a short-duration variety may help align the harvest closer to the planned date "
             "of 24 September, as sowing on 9 May would delay the harvest until 9 October.")

with app.app_context():
    from app.agents.coordinator_agent import CoordinatorAgent
    from app.extensions import db
    from app.models.notification import Notification
    from app.models.seasonal_plan import SeasonalPlan
    from app.models.task import Task
    from app.models.weather_forecast import WeatherForecast
    from app.services import decision_recommendation_service as dr
    from app.services import deferred_ai_service as deferred
    from app.services import demo_scenario_service as scenarios
    from app.services.demo_reset_service import reset_demo
    from app.services.domain_service.task_service import TaskService
    from app.services.weekly_planning_service.weekly_planner_service import WeeklyPlannerService
    from app.utils import clock, demo_flags

    demo_flags.simulator_wait_seconds = lambda uid: 0
    client = app.test_client()
    today = clock.today()
    S3 = scenarios.WINDOW_RUNNING_OUT

    def cotton_entry():
        plan = SeasonalPlan.query.filter_by(user_id=1, currently_active=True).first()
        return next(e for e in plan.entries if e.crop_name_rel.name == "Cotton")

    def sowing(crop):
        e = {x["crop_name"]: x for x in WeeklyPlannerService.show_active_plan(1)["entries"]}[crop]
        adj = next((a for a in e.get("climate_adjustments_made", []) if a.get("factor") == "sowing_window"), {})
        return adj.get("status"), [x["date"] for x in e["week_events"] if x["event_type"] == "sowing"]

    def decision_tasks():
        db.session.expire_all()
        return Task.query.filter_by(user_id=1, task_type="decision").order_by(Task.id).all()

    def active_sow_cotton():
        return Task.query.filter(Task.user_id == 1, Task.task_type == "planting", Task.title.like("Sow Cotton%"),
                                 Task.is_active.is_(True), Task.completed.is_(False)).all()

    def decision_note():
        return (Notification.query.filter_by(user_id=1, entity_type="seasonal_plan_entry")
                .filter(Notification.message.like("%decision needed%")).order_by(Notification.id.desc()).first())

    def run(key):
        r = client.post("/mytasks/1/run-weather-simulator", json={"scenario": key})
        deferred.wait(1, 30)
        return r

    # ── 1. fresh start ─────────────────────────────────────────────────────────────────
    print("\n-- fresh start")
    keys = [o["key"] for o in scenarios.options()]
    check(keys == ["typical", "heavy_rain", S3], f"three scenarios {keys}")
    s3 = next(o for o in scenarios.options() if o["key"] == S3)
    check(s3["label"] == "Sowing window running out", "short label")
    check("also changes the plan" in s3["info"].lower() and "24 April (not sown)" in s3["info"],
          "info text says the plan date changes too (24 April, not sown)")
    check(not decision_tasks(), "no decision task")
    check(cotton_entry().sowing == "05/07/2027", "cotton planned 7 May")

    # ── 2. scenario 3: decision needed, decision task, fallback (no AI) ─────────────────
    print("\n-- scenario 3: sowing window running out (placeholder AI)")
    r = run(S3)
    body = r.get_json() or {}
    check(r.status_code == 200 and "24 April" in (body.get("banner") or ""), f"ran with the banner ({r.status_code})")
    check(cotton_entry().sowing == "04/24/2027", "cotton's planned date is 24 Apr (simulated plan change)")
    st, days = sowing("Cotton")
    check(st == "decision_needed" and days == [], f"cotton: decision needed, no sowing event ({st}, {days})")
    check(sowing("Maize") == ("planned", ["2027-05-06"]), f"maize unchanged on 6 May {sowing('Maize')}")
    ds = decision_tasks()
    check(len(ds) == 1, f"one decision task ({len(ds)})")
    d = ds[0]
    check(d.title == "Decide: Cotton sowing – The Reservoir", f"title {d.title!r}")
    check(d.priority == "critical" and d.task_category == "plan" and d.due_date == today and d.is_active,
          "critical, plan, due today, active")
    check("Completing this task marks the decision as made; it does not record sowing." in d.description
          and "Sowing window 24 Apr–8 May" in d.description and "Options:" in d.description,
          "description: window, options and what completing means")
    check(not active_sow_cotton(), "no active Sow Cotton task")
    check(not Notification.query.filter_by(user_id=1, title="Sowing week ahead").count(),
          "'Sowing week ahead' removed")
    n = decision_note()
    check(n is not None and n.notification_type == "warning", "decision notification sent")
    check(d.ai_explanation == "", "placeholder AI: no recommendation (empty, not retried)")
    check(n.detail.endswith(dr.NO_RECOMMENDATION) and "Options:" in n.detail,
          "notification detail: options + 'No AI recommendation'")
    check("unusual" not in n.detail.lower() and not n.detail.startswith("{"), "decision notification keeps its own text")

    # ── 3. a usable AI answer → recommendation on the task and in the notification ──────
    print("\n-- AI answers (replaced): accepted and rejected")
    orig_call = dr._call_ai
    task_key = str(d.id)

    def answer_with(option, reason):
        dr._call_ai = lambda prompt, timeout=dr.CALL_TIMEOUT_S: json.dumps({task_key: {"option": option,
                                                                                         "reason": reason}})
        return dr.recommend(1, only_missing=False)

    res = answer_with("short_duration", LIVE_TEXT)
    db.session.expire_all()
    d = decision_tasks()[0]
    check(res["recommended"] == [d.id], f"the live answer passes the guard {res.get('rejected')}")
    check(d.ai_explanation == "Switch to a short-duration variety. " + LIVE_TEXT, "stored on the task")
    n = decision_note()
    check(f"{dr.LABEL}: Switch to a short-duration variety." in n.detail and dr.NO_RECOMMENDATION not in n.detail,
          "notification detail: 'Recommendation – the decision is yours: …' (once)")
    prompt = dr.build_prompt([dr.facts_for_task(d)])
    for part in ("Sowing window: 24 Apr–8 May", "Unsuitable days left in the window: 5 May, 6 May, 7 May, 8 May",
                 "153 days from sowing to harvest", "First suitable sowing day in the forecast: 9 May",
                 "Harvest if sown on 9 May: about 9 Oct", "sow_anyway", "skip_season",
                 "Do not add agronomic claims", "Forecast compared with the season: typical for May",
                 "sow_anyway (sow anyway with precautions): first suitable sowing day in the forecast: 9 May, "
                 "1 day(s) after the window ends; harvest about 9 Oct, within the harvest months of Kharif crops "
                 "in the rule base (Sep–Oct)",
                 "short_duration (switch to a short-duration variety): needs different seed; the app has no "
                 "variety data, so the effect on harvest is not modelled",
                 "switch_crop (switch crop): needs a new seasonal plan entry; not modelled",
                 "skip_season (skip the season): no Cotton this season on The Reservoir",
                 "Prefer the option that the facts support most directly",
                 "Do not treat the original planned harvest date as a target"):
        check(part in prompt, f"facts block: {part!r}")
    check("planned harvest 24 Sep" not in prompt, "facts block: no planned-harvest anchor")

    rejects = {
        "draft": ("sow_anyway", "* User: farmer\n* Constraints: 2-3 sentences. Sow on 9 May."),
        "invented number": ("sow_anyway", "Sowing on 9 May is one day late. It keeps 90 % of the harvest."),
        "invented date": ("sow_anyway", "The window ends on 8 May. Sow on 15 May when it is warmer."),
        "unknown option": ("plant_rice", "The window ends on 8 May. Rice would do better."),
        "one sentence": ("sow_anyway", "Sow on 9 May."),
        "four sentences": ("skip_season", "The window ends on 8 May. All days are unsuitable. "
                                          "Sowing later is possible. Skipping is calmer."),
        "claim word": ("sow_anyway", "Sowing on 9 May is one day late. Watch for pests after the showers."),
        "variety name": ("short_duration", "The window ends on 8 May. Use the variety FH-Lalazar for an earlier harvest."),
        "you must": ("sow_anyway", "The window ends on 8 May. You must sow on 9 May."),
        "other crop": ("switch_crop", "The window ends on 8 May. Switching to rice suits the showers."),
    }
    for name, (opt, reason) in rejects.items():
        res = answer_with(opt, reason)
        db.session.expire_all()
        d = decision_tasks()[0]
        why = (res["rejected"].get(d.id) or {}).get("reason")
        check(why and d.ai_explanation == "" and decision_note().detail.endswith(dr.NO_RECOMMENDATION),
              f"rejected: {name} ({why})")
    dr._call_ai = lambda prompt, timeout=dr.CALL_TIMEOUT_S: "not json at all"
    res = dr.recommend(1, only_missing=False)
    check(res["failed"] == [d.id], "unparseable answer: no recommendation")
    dr._call_ai = orig_call

    # ── 4. completing the decision task: not asked again ────────────────────────────────
    print("\n-- the farmer completes the decision task")
    TaskService.update_task(d.id, {"completed": True})
    CoordinatorAgent().daily_update(user_id=1, as_of_date=today, defer_ai=True)
    ds = decision_tasks()
    check(len(ds) == 1 and ds[0].completed, "still one (completed) decision task – not re-created")

    # ── 5. a suitable day appears → the decision task closes, the Sow task comes back ───
    print("\n-- a suitable sowing day appears (6 May hot and sunny)")
    reset_demo()
    run(S3)
    check(len([t for t in decision_tasks() if t.is_active]) == 1, "decision task open")
    region = "Punjab, Pakistan"
    fc = WeatherForecast.query.filter_by(region=region, date=today + timedelta(days=1)).first()
    fc.avg_temperature_c, fc.humidity, fc.rainfall_mm, fc.sunlight_hours = 33.0, 28, 0.0, 10.5
    db.session.commit()
    CoordinatorAgent().daily_update(user_id=1, as_of_date=today, defer_ai=True)
    st, days = sowing("Cotton")
    check(st == "window_set" and days == ["2027-05-06"], f"cotton: sowing set to 6 May ({st}, {days})")
    d = decision_tasks()[0]
    hist = json.loads(d.task_changes or "[]")
    check(not d.is_active and hist and hist[-1]["reason"] == "A suitable sowing day appeared: sowing on 6 May",
          f"decision task closed with the reason ({hist[-1]['reason'] if hist else None})")
    sow = active_sow_cotton()
    check(len(sow) == 1 and sow[0].due_date.isoformat() == "2027-05-06", "Sow Cotton task for 6 May (normal sowing task)")
    print("   … and back to no suitable day → the same decision task is reopened")
    fc.avg_temperature_c, fc.humidity, fc.rainfall_mm, fc.sunlight_hours = 27.0, 66, 6.0, 4.5
    db.session.commit()
    CoordinatorAgent().daily_update(user_id=1, as_of_date=today, defer_ai=True)
    ds = decision_tasks()
    check(len(ds) == 1 and ds[0].is_active and ds[0].id == d.id, "reopened (no duplicate)")
    check(not active_sow_cotton(), "Sow Cotton deactivated again")

    # ── 6. sowing recorded as done → the decision task closes ───────────────────────────
    print("\n-- sowing recorded as done (completed sowing task)")
    entry = cotton_entry()
    reserv = ds[0].field
    sow_task = TaskService.create_task({
        "title": "Sow Cotton – The Reservoir", "priority": "high", "task_type": "planting", "task_category": "plan",
        "due_date": today, "crop_id": ds[0].crop_id, "field_id": reserv.id if reserv else None, "user_id": 1,
        "seasonal_plan_entry_id": entry.id})
    TaskService.update_task(sow_task.id, {"completed": True})
    CoordinatorAgent().daily_update(user_id=1, as_of_date=today, defer_ai=True)
    d = decision_tasks()[0]
    hist = json.loads(d.task_changes or "[]")
    check(not d.is_active and hist[-1]["reason"] == "Sowing recorded as done on 5 May",
          f"closed: {hist[-1]['reason'] if hist else None}")

    # ── 7. another scenario restores the plan; Reset demo returns to the start ──────────
    print("\n-- scenario 1 after scenario 3, then Reset demo")
    reset_demo()
    run(S3)
    run("typical")
    check(cotton_entry().sowing == "05/07/2027", "scenario 1 restores cotton's planned date (7 May)")
    check(sowing("Cotton") == ("window_set", ["2027-05-09"]), f"scenario 1 result unchanged: cotton 9 May {sowing('Cotton')}")
    check(Notification.query.filter_by(user_id=1, title="Sowing week ahead").count() == 1, "'Sowing week ahead' back")
    check(not [t for t in decision_tasks() if t.is_active], "no open decision task")
    run(S3)
    r = client.post("/mytasks/1/reset-demo")
    check(r.status_code == 200, f"reset ({r.status_code})")
    check(cotton_entry().sowing == "05/07/2027" and not decision_tasks() and scenarios.active(1) is None,
          "Reset demo: cotton 7 May, no decision task, no scenario")
    check(sowing("Cotton") == ("planned", ["2027-05-07"]), f"starting state {sowing('Cotton')}")

print(f"\n{'ALL PASSED' if not FAILED else f'{len(FAILED)} FAILED: {FAILED}'}")
sys.exit(1 if FAILED else 0)
