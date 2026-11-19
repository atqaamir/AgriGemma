"""Simulator scenarios, Reset demo, cooldowns, heavy-rain rule (R1/R2) regression, chatbot block.

Run from the project root with DEMO_TODAY=2027-05-05 USE_PLACEHOLDER_AI=true:
    python Test_Runs/test_rain_scenario.py
Placeholder AI only. Reseeds the local DB (fresh start = calm forecast).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["SIMULATOR_COOLDOWN_SECONDS"] = "30"

FAILED = []


def check(cond, label):
    print(f"  {'OK  ' if cond else 'FAIL'} {label}")
    if not cond:
        FAILED.append(label)


from run import app  # noqa: E402  bootstrap(): reseed + calm startup forecast

with app.app_context():
    from app.agents.coordinator_agent import CoordinatorAgent
    from app.models.notification import Notification
    from app.models.plan_event_override import PlanEventOverride
    from app.models.task import Task
    from app.rules.rule_engine.rule_engine import RuleEngine
    from app.services import demo_scenario_service as scenarios
    from app.services import forecast_vs_normal_service as fvn
    from app.services.weekly_planning_service.weekly_planner_service import WeeklyPlannerService
    from app.utils import clock, demo_flags

    today = clock.today()
    client = app.test_client()

    def plan(uid=1):
        return {e["crop_name"]: e for e in WeeklyPlannerService.show_active_plan(uid)["entries"]}

    def sow(uid=1):
        return {c: [x["date"] for x in e["week_events"] if x["event_type"] == "sowing"] for c, e in plan(uid).items()}

    def overrides():
        return sorted((o.seasonal_plan_entry_id, o.event_type, o.original_date.isoformat(), o.actual_date.isoformat())
                      for o in PlanEventOverride.query.filter_by(source="forecast_shift"))

    def sow_maize_tasks():
        return [(t.due_date.isoformat(), t.is_active) for t in
                Task.query.filter(Task.user_id == 1, Task.title.like("Sow Maize%")).all()]

    def snapshot(uid):
        """Events (date, type) and override dates – the decisions, not their wording."""
        return {c: sorted((x["date"], x["event_type"]) for x in e["week_events"]) for c, e in plan(uid).items()}

    def html():
        return client.get("/mytasks/").get_data(as_text=True)

    BANNER = "Simulated scenario: unusual heavy rain for early May"

    print(f"\n-- starting state on {today} (forecast = baseline)")
    start_sow, start_tasks, start_notes = sow(), sow_maize_tasks(), Notification.query.count()
    check(start_sow == {"Maize": ["2027-05-06"], "Cotton": ["2027-05-07"]}, f"maize 6 May, cotton 7 May ({start_sow})")
    check(not overrides(), "no forecast override")
    check(start_tasks == [("2027-05-06", True)], f"Sow Maize task for tomorrow ({start_tasks})")
    check(fvn.build(1) is None and scenarios.active(1) is None, "no forecast change: no chatbot block, no scenario")
    page = html()
    check('id="weatherScenarioSelect"' in page and ">Typical May weather</option>" in page
          and ">Unusual heavy rain</option>" in page and "Unexpected change: heavy rain, unusual for early May" in page and 'id="resetDemoBtn"' in page,
          "simulator card: scenario dropdown + Reset demo button")
    check(BANNER not in page.split('id="demoScenarioBannerText">')[1][:80], "no scenario banner")

    print("\n-- R1/R2 regression: users 2 and 3 (heatwave) and the starting state unchanged")
    saved = (RuleEngine.SEEDBED_RAIN_MM, RuleEngine.WEEKLY_RAIN_TOTAL)
    results = {}
    for label, (mm, total) in (("off", (1e9, False)), ("on", saved)):
        RuleEngine.SEEDBED_RAIN_MM, RuleEngine.WEEKLY_RAIN_TOTAL = mm, total
        for uid in (1, 2, 3):
            CoordinatorAgent().startup_forecast(uid)
        results[label] = {uid: snapshot(uid) for uid in (1, 2, 3)}
        results[label]["overrides"] = overrides()
    RuleEngine.SEEDBED_RAIN_MM, RuleEngine.WEEKLY_RAIN_TOTAL = saved
    for uid in (1, 2, 3):
        check(results["off"][uid] == results["on"][uid], f"user {uid}: same events with and without R1/R2")
    check(results["off"]["overrides"] == results["on"]["overrides"] == [], "no overrides either way")

    print("\n-- scenario 1: expected change, typical early-May weather")
    r = client.post("/mytasks/1/run-weather-simulator", json={"scenario": "typical"})
    body = r.get_json() or {}
    check(r.status_code == 200 and body.get("banner") is None, f"ran, no banner ({r.status_code})")
    check(sow() == {"Maize": ["2027-05-06"], "Cotton": ["2027-05-09"]}, f"cotton 7 → 9 May, maize 6 May ({sow()})")
    ov = overrides()
    check([o[1:] for o in ov if o[1] != "irrigation"] == sorted([
        ("fertilization", "2027-06-01", "2027-06-03"), ("harvesting", "2027-10-07", "2027-10-09"),
        ("irrigation_start", "2027-05-17", "2027-05-19"), ("sowing", "2027-05-07", "2027-05-09")]),
        f"cotton cascades: harvest 9 Oct, irrigation start 19 May, fertilization 3 Jun ({ov})")
    check(sow_maize_tasks() == [("2027-05-06", True)], "no task move (Sow Maize stays on 6 May)")
    check(Notification.query.count() > start_notes, "change notification")
    data = fvn.build(1)
    text = fvn.block(data)
    check(data["verdict"] == "typical" and "typical for the season" in text
          and "app's normal for May" in text and "8 mm rain on 2 days" in text, "chatbot block: typical for the season")
    check("temperature 20–30 °C" in text and "sunlight 4–8 h" in text, "chatbot block: the cotton rules")

    print("\n-- simulator cooldown (30 s)")
    r = client.post("/mytasks/1/run-weather-simulator", json={"scenario": "heavy_rain"})
    check(r.status_code == 429 and r.headers.get("Retry-After"), f"second run within 30 s → 429 ({r.status_code})")
    check(sow()["Maize"] == ["2027-05-06"], "nothing changed by the refused run")
    cd = client.get("/mytasks/1/demo-cooldowns").get_json()
    cd2 = client.get("/mytasks/1/demo-cooldowns").get_json()
    check(1 <= cd["simulator"] <= 30 and cd["reset"] == 0 and cd2["simulator"] <= cd["simulator"],
          f"status endpoint: simulator {cd['simulator']} s left, reset 0, read-only ({cd2})")
    r = client.post("/mytasks/1/run-weather-simulator", json={"scenario": "nope"})
    check(r.status_code == 400, f"unknown scenario → 400 ({r.status_code})")
    os.environ["SIMULATOR_COOLDOWN_SECONDS"] = "0"

    print("\n-- scenario 2: unexpected change, heavy rain unusual for early May")
    notes_before = Notification.query.count()
    r = client.post("/mytasks/1/run-weather-simulator", json={"scenario": "heavy_rain"})
    body = r.get_json() or {}
    check(r.status_code == 200 and body.get("banner") == BANNER, f"ran with the banner ({r.status_code})")
    check(sow() == {"Maize": ["2027-05-10"], "Cotton": ["2027-05-10"]}, f"maize 6 → 10 May, cotton → 10 May ({sow()})")
    ov = overrides()
    check(sum(1 for o in ov if o[1] == "sowing") == 2 and any(o[1:] == ("harvesting", "2027-10-06", "2027-10-10")
                                                              for o in ov),
          "overrides: both sowings, maize harvest 10 Oct")
    sowing_text = next(a["adjustment"] for a in plan()["Maize"]["climate_adjustments_made"]
                       if a["factor"] == "sowing_window")
    check("soil moisture >60 % (seed bed after ≥20 mm rain)" in sowing_text, f"reason: {sowing_text[:90]}…")
    check(not any("Dry week" in (a.get("adjustment") or "") for a in plan()["Maize"]["climate_adjustments_made"]),
          "no 'Dry week' with 145 mm of rain (R2)")
    sm = Task.query.filter(Task.user_id == 1, Task.title.like("Sow Maize%"), Task.is_active.is_(True)).all()
    check(len(sm) == 1 and sm[0].due_date.isoformat() == "2027-05-10" and sm[0].ai_explanation,
          f"Sow Maize task moved to 10 May, with a 'Why' explanation ({sow_maize_tasks()})")
    check(Notification.query.count() > notes_before, "change notification")
    check(BANNER in html(), "banner on the page")
    data = fvn.build(1)
    text = fvn.block(data)
    check(data["verdict"] == "unusual" and "[UNUSUAL WEATHER]" in text and "145 mm of rain in 7 days" in text
          and "8 mm for the whole month of May" in text, "chatbot block: unusual compared to the app's normal for May")
    check("Waterlogged seed-beds" in text and "Sow Maize – Punjab Wheat Belt: moved from 2027-05-06 to 2027-05-10"
          in text, "chatbot block: rule reasons + task move")
    check("on record" not in text.lower(), "no invented claims from seed notes in the block")
    ctx_prompt = __import__("app.services.intelligence_service.chatbot_service.prompts._prompt_chatbot_service",
                            fromlist=["CHATBOT_SYSTEM"]).CHATBOT_SYSTEM
    check("re-checks the forecast every morning" in ctx_prompt and "statistics" in ctx_prompt, "prompt rule 10")

    print("\n-- back to scenario 1 without a reset")
    client.post("/mytasks/1/run-weather-simulator", json={"scenario": "typical"})
    check(sow() == {"Maize": ["2027-05-06"], "Cotton": ["2027-05-09"]}, f"maize back to 6 May, cotton 9 May ({sow()})")
    check([d for d, a in sow_maize_tasks() if a] == ["2027-05-06"], f"Sow Maize task back on 6 May ({sow_maize_tasks()})")
    check(BANNER not in html().split('id="demoScenarioBannerText">')[1][:80], "banner gone")

    print("\n-- Reset demo (DEMO_ADMIN_ENABLED unset)")
    os.environ["DEMO_ADMIN_ENABLED"] = ""
    client.post("/mytasks/1/run-weather-simulator", json={"scenario": "heavy_rain"})
    r = client.post("/mytasks/1/reset-demo")
    check(not demo_flags.admin_enabled() and r.status_code == 200, f"reset works with admin off ({r.status_code})")
    check(sow() == start_sow and not overrides() and sow_maize_tasks() == start_tasks,
          f"back to the starting state ({sow()}, tasks {sow_maize_tasks()})")
    check(Notification.query.count() == start_notes, "notifications back to the fresh-start set")
    check(scenarios.active(1) is None and fvn.build(1) is None and BANNER not in
          html().split('id="demoScenarioBannerText">')[1][:80], "scenario cleared, no banner, no chatbot block")
    r = client.post("/mytasks/1/reset-demo")
    check(r.status_code == 429 and r.headers.get("Retry-After"), f"second reset within 60 s → 429 ({r.status_code})")
    cd = client.get("/mytasks/1/demo-cooldowns").get_json()
    check(50 <= cd["reset"] <= 60, f"status endpoint: reset {cd['reset']} s left")
    check(client.post("/mytasks/1/run-refresh-data").status_code == 403, "Refresh Data stays admin-only (403)")

    print("\n-- scenario can be run again after the reset")
    client.post("/mytasks/1/run-weather-simulator", json={"scenario": "heavy_rain"})
    check(sow() == {"Maize": ["2027-05-10"], "Cotton": ["2027-05-10"]}, "heavy rain again: both on 10 May")

print(f"\n{'ALL PASSED' if not FAILED else f'{len(FAILED)} FAILED: {FAILED}'}")
sys.exit(1 if FAILED else 0)
