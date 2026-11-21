"""Fixes from the live test of 0d3f782 – no AI, placeholder provider.

Run from the project root with DEMO_TODAY=2027-05-05 USE_PLACEHOLDER_AI=true:
    python Test_Runs/test_live_fixes.py
1. Chat in scenario 3 knows the decision: context (core summary, decision block, plan line without
   harvest dates), the rule-based answer, and a Sow task on hold is never "cancelled".
2. "Sow anyway" uses the first suitable day (9 May), else tomorrow – and says which.
3. Harvest card: "decision pending" / "skipped" instead of a harvest date.
4. Re-running a scenario creates its change notification again (no 30-min duplicate drop).
5. Recommended order: no reason refers to the task itself.
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

Q = "What should I do about my cotton?"
REC = ("Sow anyway with precautions. The sowing window ends on 8 May, but no suitable days were available within "
       "that period. Sowing on 9 May is the first suitable day in the forecast, and this date results in a harvest "
       "around 9 October, which falls within the expected harvest months.")

with app.app_context():
    from app.agents.coordinator_agent import CoordinatorAgent
    from app.extensions import db
    from app.models.notification import Notification
    from app.models.seasonal_plan import SeasonalPlan
    from app.models.task import Task
    from app.models.weather_forecast import WeatherForecast
    from app.services import deferred_ai_service as deferred
    from app.services import forecast_vs_normal_service as fvn
    from app.services import task_insights_service as ti
    from app.services.demo_reset_service import reset_demo
    from app.services.intelligence_service.chatbot_service.chatbot_service import ChatbotService, _format_farmer_context
    from app.services.intelligence_service.context import context_builder as cb
    from app.services.intelligence_service.intent.intent_classifier import FarmIntent, classify
    from app.utils import clock, demo_flags

    demo_flags.simulator_wait_seconds = lambda uid: 0
    client = app.test_client()
    today = clock.today()

    def run(key):
        r = client.post("/mytasks/1/run-weather-simulator", json={"scenario": key})
        deferred.wait(1, 30)
        return r

    def decision_task():
        db.session.expire_all()
        return Task.query.filter_by(user_id=1, task_type="decision").order_by(Task.id.desc()).first()

    def cotton_entry():
        db.session.expire_all()
        plan = SeasonalPlan.query.filter_by(user_id=1, currently_active=True).first()
        return next(e for e in plan.entries if e.crop_name_rel.name == "Cotton")

    def chat(question):
        ir = classify(question)
        ctx = cb.build_chatbot_context(1, ir)
        return ir, ctx, _format_farmer_context(ctx, question, ir)

    # ── 1. chat knows the decision ─────────────────────────────────────────────────────
    print("\n-- 1. chat in scenario 3")
    reset_demo()
    run("window_running_out")
    d = decision_task()
    d.ai_explanation = REC
    db.session.commit()
    for q in (Q, "When should I sow cotton?", "What are my tasks today?"):
        ir, ctx, text = chat(q)
        check("[SOWING DECISION NEEDED" in text and "Decide: Cotton sowing – The Reservoir" in text
              and "Recommendation (shown to the farmer" in text and "Sow anyway with precautions." in text
              and "Options: sow anyway with precautions" in text and "not cancelled" in text,
              f"{ir.primary.value}: decision block with the task, options and recommendation")
    ir, ctx, text = chat(Q)
    plan_line = next(l for l in text.splitlines() if l.strip().startswith("Cotton (The Reservoir):"))
    check("harvest" not in plan_line.split("–")[0] and "24 Sep" not in plan_line and "until the farmer decides" in plan_line,
          f"plan line: no harvest / irrigation dates ({plan_line.strip()[:110]}…)")
    check("Cotton decision needed (open Decide task; recommended: sow anyway with precautions; the farmer decides)"
          in ctx["core"] and len(ctx["core"]) <= cb.CORE_MAX_CHARS, f"core summary ({len(ctx['core'])} chars)")
    check("cancelled" not in text.lower().replace("not cancelled", "").replace("'cancelled'", ""),
          "context never calls anything cancelled")
    fb = ChatbotService._build_fallback_response(Q, ctx, 1)
    print("     " + fb.replace("\n", "\n     ")[:600])
    check("decision needed" in fb and "Recommendation – the decision is yours: Sow anyway with precautions." in fb
          and "Decide: Cotton sowing" in fb and fb.rstrip().endswith("the decision is yours.")
          and "cancel" not in fb.lower(), "rule-based answer: decision, recommendation, the farmer decides")
    fb2 = ChatbotService._build_fallback_response("Is my cotton ok?", cb.build_chatbot_context(1, classify("Is my cotton ok?")), 1)
    check("Sowing decision:" in fb2 and "decision needed" in fb2, "rule-based answer for a question naming cotton")

    print("   a Sow task put on hold by the decision is not 'cancelled'")
    region = "Punjab, Pakistan"
    fc = WeatherForecast.query.filter_by(region=region, date=today + timedelta(days=1)).first()
    fc.avg_temperature_c, fc.humidity, fc.rainfall_mm, fc.sunlight_hours = 33.0, 28, 0.0, 10.5
    db.session.commit()
    CoordinatorAgent().daily_update(user_id=1, as_of_date=today, defer_ai=True)     # Sow Cotton 6 May appears
    fc.avg_temperature_c, fc.humidity, fc.rainfall_mm, fc.sunlight_hours = 27.0, 66, 6.0, 4.5
    db.session.commit()
    CoordinatorAgent().daily_update(user_id=1, as_of_date=today, defer_ai=True)     # decision again: on hold
    changes = fvn._task_changes(1, today)
    print("     task changes: " + " | ".join(changes))
    check(any(c.startswith("Sow Cotton") and "on hold – sowing decision needed" in c for c in changes)
          and not any("Sow Cotton" in c and "cancelled" in c for c in changes), "Sow Cotton: on hold, not cancelled")
    ir, ctx, text = chat(Q)
    check("cancelled" not in text.lower().replace("not cancelled", "").replace("'cancelled'", ""),
          "context after the hold: still nothing 'cancelled'")

    # ── 2. Sow anyway on the first suitable day ────────────────────────────────────────
    print("\n-- 2. Sow anyway date")
    reset_demo()
    run("window_running_out")
    d = decision_task()
    r = client.get(f"/mytasks/1/decision/{d.id}/sow-anyway-date")
    check(r.status_code == 200 and r.get_json() == {"date": "2027-05-09", "first_suitable": True},
          f"date for the confirmation: 9 May, the first suitable day {r.get_json()}")
    r = client.post(f"/mytasks/1/decision/{d.id}/sow-anyway")
    deferred.wait(1, 30)
    body = r.get_json() or {}
    check(r.status_code == 200 and body.get("date") == "2027-05-09", f"sown anyway on 9 May {body}")
    sow = Task.query.filter(Task.user_id == 1, Task.title.like("Sow Cotton%"), Task.is_active.is_(True),
                            Task.completed.is_(False)).all()
    check(len(sow) == 1 and sow[0].due_date.isoformat() == "2027-05-09" and "first suitable sowing day" in (sow[0].notes or ""),
          f"Sow Cotton due 9 May with its note ({[(t.due_date, t.notes) for t in sow]})")
    print("   no suitable day in the forecast → tomorrow")
    reset_demo()
    run("window_running_out")
    for off in (4, 5, 6):
        f = WeatherForecast.query.filter_by(region=region, date=today + timedelta(days=off)).first()
        f.avg_temperature_c, f.sunlight_hours = 27.0, 5.0
    db.session.commit()
    CoordinatorAgent().daily_update(user_id=1, as_of_date=today, defer_ai=True)
    d = decision_task()
    r = client.get(f"/mytasks/1/decision/{d.id}/sow-anyway-date")
    check(r.get_json() == {"date": "2027-05-06", "first_suitable": False}, f"tomorrow, not 'first suitable' {r.get_json()}")
    r = client.post(f"/mytasks/1/decision/{d.id}/sow-anyway")
    deferred.wait(1, 30)
    sow = Task.query.filter(Task.user_id == 1, Task.title.like("Sow Cotton%"), Task.is_active.is_(True)).all()
    check(r.get_json().get("date") == "2027-05-06" and sow and "no suitable sowing day in the forecast, so tomorrow"
          in (sow[0].notes or ""), "sown tomorrow, note says why")

    # ── 3. harvest card ────────────────────────────────────────────────────────────────
    print("\n-- 3. harvest card")
    reset_demo()
    data = client.get("/mytasks/1/upcoming-harvest").get_json()
    check([c["crop"] for c in data["crops"]] == ["Maize", "Cotton"] and all(c["harvest"] for c in data["crops"]),
          "fresh start: both crops with a harvest date")
    run("window_running_out")
    data = client.get("/mytasks/1/upcoming-harvest").get_json()
    cotton = next(c for c in data["crops"] if c["crop"] == "Cotton")
    check(cotton["status"] == "decision_pending" and cotton["harvest"] is None, f"cotton: decision pending, no date {cotton}")
    check(data["earliest"] == data["latest"] == "2027-10-06", f"window from maize only ({data['earliest']}–{data['latest']})")
    d = decision_task()
    client.post(f"/mytasks/1/decision/{d.id}/skip-season")
    deferred.wait(1, 30)
    cotton = next(c for c in client.get("/mytasks/1/upcoming-harvest").get_json()["crops"] if c["crop"] == "Cotton")
    check(cotton["status"] == "skipped" and cotton["harvest"] is None, "cotton: skipped, no date")
    client.post(f"/mytasks/1/seasonal-entry/{cotton_entry().id}/undo-decision")
    deferred.wait(1, 30)
    d = decision_task()
    client.post(f"/mytasks/1/decision/{d.id}/sow-anyway")
    deferred.wait(1, 30)
    cotton = next(c for c in client.get("/mytasks/1/upcoming-harvest").get_json()["crops"] if c["crop"] == "Cotton")
    check(cotton["status"] is None and cotton["harvest"] == "2027-10-09", f"sow anyway: harvest date again {cotton}")

    # ── 4. re-running a scenario notifies again ───────────────────────────────────────
    print("\n-- 4. every change notification is created")
    reset_demo()
    counts = []
    for key in ("typical", "heavy_rain", "typical", "typical"):
        run(key)
        counts.append(Notification.query.filter_by(user_id=1, notification_type="change").count())
    check(counts == [1, 2, 3, 4], f"one change notification per run {counts}")
    msgs = [n.message for n in Notification.query.filter_by(user_id=1, notification_type="change").order_by(Notification.id)]
    check(msgs[2] == msgs[3], f"Light showers twice in a row: same message, both created ({msgs[3]!r})")

    # ── 5. recommended order: no self-reference ──────────────────────────────────────
    print("\n-- 5. recommended order reasons")
    reset_demo()
    order = client.get("/mytasks/recommended-order?user_id=1").get_json()["order"]
    titles = {t.id: t.title for t in Task.query.filter_by(user_id=1).all()}
    for o in order:
        check(not ti.self_referencing(o["reason"], titles[o["task_id"]]), f"{titles[o['task_id']]}: {o['reason']}")
    sow_maize = next(o for o in order if titles[o["task_id"]].startswith("Sow Maize"))
    check(sow_maize["reason"] == "High priority, due tomorrow – the planned sowing date (6 May).",
          f"Sow Maize: {sow_maize['reason']}")
    print("   a stored insight reason that refers to the task itself is replaced")
    stored = ti.generate(1)
    from app.models.ai_insight_report import AiInsightReport
    row = AiInsightReport.query.filter_by(user_id=1, kind="task_insights").order_by(AiInsightReport.id.desc()).first()
    data = json.loads(row.data)
    for x in data["priority_order"]:
        if x["title"].startswith("Sow Maize"):
            x["reason"] = "Before Sow Maize 6 May."
    row.data = json.dumps(data)
    db.session.commit()
    body = client.get("/mytasks/recommended-order?user_id=1").get_json()
    sm = next(o for o in body["order"] if titles[o["task_id"]].startswith("Sow Maize"))
    check(body["source"] == "insights" and sm["source"] == "rule" and "before Sow Maize" not in sm["reason"],
          f"replaced by the rule reason ({sm['reason']})")
    reset_demo()

print(f"\n{'ALL PASSED' if not FAILED else f'{len(FAILED)} FAILED: {FAILED}'}")
sys.exit(1 if FAILED else 0)
