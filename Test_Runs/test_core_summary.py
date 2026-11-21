"""Core summary in every chatbot context (scenario, sowing status per crop, today's and tomorrow's
pending tasks; <= 400 chars) and the context budgets – no AI, placeholder provider.

Run from the project root with DEMO_TODAY=2027-05-05 USE_PLACEHOLDER_AI=true:
    python Test_Runs/test_core_summary.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FAILED = []


def check(cond, label):
    print(f"  {'OK  ' if cond else 'FAIL'} {label}")
    if not cond:
        FAILED.append(label)


from run import app  # noqa: E402

QUESTIONS = ["hi", "When should I irrigate the maize?", "What is the weather this week?", "When is the harvest?",
             "Should I add fertilizer?", "How is my soil?", "What are my tasks today?", "Any alerts?",
             "When should I sow cotton?", "Tell me about my farm"]

with app.app_context():
    from app.services import deferred_ai_service as deferred
    from app.services import demo_scenario_service as scenarios
    from app.services.demo_reset_service import reset_demo
    from app.services.intelligence_service.chatbot_service.chatbot_service import _format_farmer_context
    from app.services.intelligence_service.context import context_builder as cb
    from app.services.intelligence_service.context.token_budget import BUDGET_CHATBOT_CONTEXT
    from app.services.intelligence_service.intent.intent_classifier import FarmIntent, classify
    from app.models.task import Task
    from app.utils import demo_flags

    demo_flags.simulator_wait_seconds = lambda uid: 0
    client = app.test_client()

    def core():
        return cb._fetch_core(1)

    def contexts():
        """(question, intent, formatted context, budget) for every question."""
        from app.services import forecast_vs_normal_service as fvn
        out = []
        for q in QUESTIONS:
            ir = classify(q)
            ctx = cb.build_chatbot_context(1, ir)
            text = _format_farmer_context(ctx, q, ir)
            budget = (4_000 if ir.primary in (FarmIntent.TASK, FarmIntent.GENERAL) else BUDGET_CHATBOT_CONTEXT) \
                + len(fvn.block(ctx.get("forecast_vs_normal")))
            out.append((q, ir.primary.value, text, budget, ctx.get("core")))
        return out

    def check_contexts(tag):
        for q, intent, text, budget, c in contexts():
            ok = bool(c) and c in text and text.index(c) < 60 and len(text) <= budget
            check(ok, f"{tag}: {intent:<13} core first in the context, {len(text)} <= {budget} chars")

    print("\n-- fresh start")
    c = core()
    print("   " + c)
    check(len(c) <= cb.CORE_MAX_CHARS, f"{len(c)} chars (<= {cb.CORE_MAX_CHARS})")
    for part in ("CORE: scenario none.", "Maize sowing 6 May", "Cotton sowing 7 May", "Rice not feasible",
                 "Today: ", "Tomorrow: ", "Sow Maize – Punjab Wheat Belt (high)"):
        check(part in c, f"has {part!r}")
    check_contexts("fresh")

    print("\n-- scenario 3: decision needed")
    client.post("/mytasks/1/run-weather-simulator", json={"scenario": scenarios.WINDOW_RUNNING_OUT})
    deferred.wait(1, 30)
    c = core()
    print("   " + c)
    check(len(c) <= cb.CORE_MAX_CHARS, f"{len(c)} chars")
    for part in ("scenario Sowing window running out", "Cotton decision needed",
                 "Decide: Cotton sowing – The Reservoir (critical)", "Rice not feasible", "Maize sowing 6 May"):
        check(part in c, f"has {part!r}")
    check_contexts("scenario 3")

    print("\n-- sow anyway, then skip")
    d = Task.query.filter_by(user_id=1, task_type="decision").first()
    client.post(f"/mytasks/1/decision/{d.id}/sow-anyway")
    deferred.wait(1, 30)
    c = core()
    print("   " + c)
    check("Cotton sow anyway 9 May (farmer)" in c, "sow anyway on the first suitable day (9 May)")
    from app.models.seasonal_plan import SeasonalPlan
    entry = next(e for e in SeasonalPlan.query.filter_by(user_id=1, currently_active=True).first().entries
                 if e.crop_name_rel.name == "Cotton")
    client.post(f"/mytasks/1/seasonal-entry/{entry.id}/undo-decision")
    deferred.wait(1, 30)
    d = Task.query.filter_by(user_id=1, task_type="decision").first()
    client.post(f"/mytasks/1/decision/{d.id}/skip-season")
    deferred.wait(1, 30)
    c = core()
    print("   " + c)
    check("Cotton skipped by the farmer" in c and "Decide:" not in c, "skipped, no decision task")

    print("\n-- overdue (weekly plan status patched)")
    from app.services.weekly_planning_service.weekly_planner_service import WeeklyPlannerService
    orig = WeeklyPlannerService.show_active_plan
    entry.skipped_on = None
    from app.extensions import db
    db.session.commit()

    def patched(uid):
        p = orig(uid)
        for e in p["entries"]:
            if e["crop_name"] == "Cotton":
                e["sowing_status"], e["week_events"] = "overdue", []
        return p

    WeeklyPlannerService.show_active_plan = staticmethod(patched)
    c = core()
    WeeklyPlannerService.show_active_plan = orig
    check("Cotton sowing overdue, decision needed" in c, f"overdue label ({c[:120]})")

    print("\n-- many tasks: still <= 400 chars")
    from app.services.domain_service.task_service import TaskService
    from app.utils import clock
    for i in range(25):
        TaskService.create_task({"title": f"Check drip line section {i} near the reservoir channel",
                                 "priority": "medium", "task_type": "maintenance", "task_category": "field",
                                 "due_date": clock.today(), "user_id": 1})
    c = core()
    print("   " + c)
    check(len(c) <= cb.CORE_MAX_CHARS and "more" in c, f"{len(c)} chars, '+N more'")
    check_contexts("many tasks")
    reset_demo()

print(f"\n{'ALL PASSED' if not FAILED else f'{len(FAILED)} FAILED: {FAILED}'}")
sys.exit(1 if FAILED else 0)
