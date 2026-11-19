"""Startup applies the forecast (plan roll + forecast + plan task sync) — no AI, no notifications.

Run from the project root with DEMO_TODAY=2027-05-05 USE_PLACEHOLDER_AI=true:
    python Test_Runs/test_startup_forecast.py
Counts AI calls and sowing-decision notifications from before the app is created, then
checks the starting state (forecast = baseline: maize 6 May, cotton 7 May, no forecast change)
and that scenario 1 ("typical early-May weather") moves cotton to 9 May.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FAILED = []


def check(cond, label):
    print(f"  {'OK  ' if cond else 'FAIL'} {label}")
    if not cond:
        FAILED.append(label)


# Count every AI entry point and the only notification the forecast step can send.
from app.services.ai_model_service import ai_model_service  # noqa: E402
from app.services.weekly_planning_service.weekly_planner_service import WeeklyPlannerService  # noqa: E402

COUNT = {"ai": [], "notify": 0}
for name in ("complete", "stream_complete", "fast_complete", "fast_complete_json", "fast_complete_direct",
             "fast_stream_complete"):
    orig = getattr(ai_model_service, name, None)
    if orig:
        def wrapped(*a, _orig=orig, _name=name, **k):
            COUNT["ai"].append(_name)
            return _orig(*a, **k)
        setattr(ai_model_service, name, wrapped)
# The change-notification text skips the model with the placeholder provider (rule-based
# text instead), so count its AI step too.
from app.services import change_notification_text as _cnt  # noqa: E402
_orig_cnt_ai = _cnt._call_ai


def _count_cnt(*a, **k):
    COUNT["ai"].append("change_notification_text")
    return _orig_cnt_ai(*a, **k)


_cnt._call_ai = _count_cnt
_orig_notify = WeeklyPlannerService._notify_sowing_decision


def _count_notify(*a, **k):
    COUNT["notify"] += 1
    return _orig_notify(*a, **k)


WeeklyPlannerService._notify_sowing_decision = staticmethod(_count_notify)

from run import app  # noqa: E402  bootstrap(): reseed + startup forecast

print("\n-- fresh start (forecast = baseline), before any simulator click")
startup_ai, startup_notify = list(COUNT["ai"]), COUNT["notify"]
check(not startup_ai, f"0 AI calls during startup ({startup_ai or 'none'})")
check(startup_notify == 0, f"0 sowing-decision notification calls during startup ({startup_notify})")

with app.app_context():
    from app.models.notification import Notification
    from app.models.plan_event_override import PlanEventOverride
    from app.models.task import Task
    from app.services import insight_signals_service as sig
    from app.utils import clock

    today = clock.today()
    entries = {e["crop_name"]: e for e in WeeklyPlannerService.show_active_plan(1)["entries"]}
    sow = lambda crop: [x["date"] for x in entries[crop]["week_events"] if x["event_type"] == "sowing"]
    check(sow("Cotton") == ["2027-05-07"], f"cotton sowing on 7 May, as planned ({sow('Cotton')})")
    check(sow("Maize") == ["2027-05-06"], f"maize on 6 May, as planned ({sow('Maize')})")
    check(PlanEventOverride.query.filter_by(source="forecast_shift").count() == 0,
          "no forecast override (the forecast equals the baseline)")
    sow_maize = Task.query.filter(Task.user_id == 1, Task.title.like("Sow Maize%"), Task.is_active.is_(True)).all()
    check(len(sow_maize) == 1 and sow_maize[0].due_date.isoformat() == "2027-05-06",
          "plan task 'Sow Maize' for tomorrow created at startup")
    check(all(t.ai_explanation is None for t in Task.query.filter_by(task_category="plan").all()),
          "plan tasks have no explanation yet (no AI at startup; the next run explains them)")
    signals = sig.build_signals(1)
    check(not any(s["key"].startswith("weather:rain") for s in signals)
          and "9 May" not in " ".join(s["text"] for s in signals),
          "signals: no rain signal, nothing on 9 May (only the plan's dry-week signal)")
    n_notifications = Notification.query.count()

    print("\n-- scenario 1 'typical early-May weather' (simulator route, full daily update)")
    r = app.test_client().post("/mytasks/1/run-weather-simulator", json={"scenario": "typical"})
    body = r.get_json() or {}
    check(r.status_code == 200 and body.get("scenario") == "typical" and body.get("banner") is None,
          f"simulator ran scenario 1, no banner ({r.status_code})")
    entries = {e["crop_name"]: e for e in WeeklyPlannerService.show_active_plan(1)["entries"]}
    check(sow("Cotton") == ["2027-05-09"], f"cotton moves 7 → 9 May ({sow('Cotton')})")
    check(sow("Maize") == ["2027-05-06"], f"maize stays on 6 May ({sow('Maize')})")
    shifts = PlanEventOverride.query.filter_by(source="forecast_shift", event_type="sowing").all()
    check([(o.original_date.isoformat(), o.actual_date.isoformat()) for o in shifts] == [("2027-05-07", "2027-05-09")],
          "one forecast override: cotton sowing 7 → 9 May")
    check(Notification.query.count() > n_notifications, "the scenario sends its change notification")
    check(len(COUNT["ai"]) > len(startup_ai), f"the scenario makes its AI calls ({len(COUNT['ai']) - len(startup_ai)})")
    texts = " ".join(s["text"] for s in sig.build_signals(1))
    check("sowing on The Reservoir is planned for 9 May" in texts, "signals see cotton on 9 May")

    from app.agents.coordinator_agent import CoordinatorAgent
    CoordinatorAgent().daily_update(user_id=1, as_of_date=today)
    entries = {e["crop_name"]: e for e in WeeklyPlannerService.show_active_plan(1)["entries"]}
    check(sow("Cotton") == ["2027-05-09"] and
          PlanEventOverride.query.filter_by(source="forecast_shift", event_type="sowing").count() == 1,
          "a second daily update: cotton still 9 May, no duplicate override")

print(f"\n{'ALL PASSED' if not FAILED else f'{len(FAILED)} FAILED: {FAILED}'}")
sys.exit(1 if FAILED else 0)
