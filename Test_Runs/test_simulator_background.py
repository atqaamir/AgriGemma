"""Simulator: the response doesn't wait for the AI; AI texts follow in the background – no AI,
placeholder provider (the AI calls are replaced by slow / blocking stand-ins).

Run from the project root with DEMO_TODAY=2027-05-05 USE_PLACEHOLDER_AI=true:
    python Test_Runs/test_simulator_background.py
Checks: response time with a slow AI, rule-based text first and the AI text afterwards, a newer
run makes the older run's background work stale (it never overwrites), failures are logged.
"""
import json
import logging
import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FAILED = []


def check(cond, label):
    print(f"  {'OK  ' if cond else 'FAIL'} {label}")
    if not cond:
        FAILED.append(label)


from run import app  # noqa: E402  bootstrap(): reseed + calm startup forecast

TEXT_A = "Ahmad Khan, cotton at The Reservoir moves from 7 May to 9 May because 7 and 8 May are too cool."
TEXT_B = "Ahmad Khan, this much rain is unusual for early May, so maize and cotton sowing move to 10 May."
SLOW_S = 3.0


class Capture(logging.Handler):
    def __init__(self):
        super().__init__(logging.INFO)
        self.records = []

    def emit(self, record):
        self.records.append(record)


with app.app_context():
    from app.models.notification import Notification
    from app.services import change_notification_text as cnt
    from app.services import deferred_ai_service as deferred
    from app.services import plan_task_explanation_service as explanations
    from app.services.demo_reset_service import reset_demo
    from app.utils import demo_flags

    demo_flags.simulator_wait_seconds = lambda uid: 0          # no cooldown between the runs here
    client = app.test_client()
    capture = Capture()
    logging.getLogger("app.services.deferred_ai_service").addHandler(capture)

    def simulate(key):
        t0 = time.monotonic()
        r = client.post("/mytasks/1/run-weather-simulator", json={"scenario": key})
        return r, time.monotonic() - t0

    def change_notes():
        return Notification.query.filter_by(user_id=1, notification_type="change").order_by(Notification.id).all()

    def summary(n):
        from app.extensions import db
        db.session.refresh(n)
        d = json.loads(n.detail)
        return d["ai_summary"], d.get("ai_summary_source")

    # ── 1. a slow AI does not slow down the response ───────────────────────────────────────
    print(f"\n-- the AI takes {SLOW_S:g} s per call")
    reset_demo()
    orig_expl = explanations._call_ai

    def slow_cnt(prompt):
        time.sleep(SLOW_S)
        return TEXT_A

    def slow_expl(prompt, facts):
        time.sleep(SLOW_S)
        return orig_expl(prompt, facts)

    cnt._call_ai = slow_cnt
    explanations._call_ai = slow_expl
    from app.extensions import db
    from app.models.task import Task

    def unexplained_plan_tasks():
        db.session.expire_all()
        return Task.query.filter(Task.user_id == 1, Task.task_category == "plan", Task.completed.is_(False),
                                 Task.is_active.is_(True), Task.ai_explanation.is_(None)).all()

    r, dt = simulate("typical")
    pending = [t.id for t in unexplained_plan_tasks()]
    check(bool(pending), f"right away: plan tasks without a 'Why' text yet {pending}")
    check(r.status_code == 200, f"HTTP {r.status_code}")
    check(dt < SLOW_S, f"response in {dt:.2f} s (< {SLOW_S:g} s: does not wait for the AI)")
    notes = change_notes()
    check(len(notes) == 1, "change notification exists right away")
    text, source = summary(notes[-1])
    check(source == "rules" and "Cotton (The Reservoir): sowing moved from 7 May to 9 May" in text,
          "right away: rule-based text")
    alert = Notification.query.filter(Notification.user_id == 1,
                                      Notification.notification_type.in_(("alert", "warning"))).all()
    check(alert and alert[-1].detail == text, "alert detail: the same rule-based text right away")
    t0 = time.monotonic()
    check(deferred.wait(1, 30), "background run finishes")
    print(f"     background AI took {time.monotonic() - t0 + dt:.1f} s after the click")
    text, source = summary(notes[-1])
    check(source == "ai" and text == TEXT_A, "afterwards: the AI text in the pop-up report")
    db.session.refresh(alert[-1])
    check(alert[-1].detail == TEXT_A, "afterwards: the AI text in the alert detail")
    left = [t.id for t in unexplained_plan_tasks()]
    check(not left and all(Task.query.get(i).ai_explanation for i in pending),
          f"afterwards: those tasks have their 'Why' text (left: {left})")
    explanations._call_ai = orig_expl

    # ── 2. a newer run makes the older background work stale ─────────────────────────────
    print("\n-- run A's AI is still writing when run B starts")
    reset_demo()
    release = threading.Event()

    def blocking_cnt(prompt):
        if "Forecast verdict: unusual" in prompt:
            return TEXT_B                  # run B (heavy rain) answers at once
        release.wait(20)                   # run A (typical) blocks until B has started
        return TEXT_A

    cnt._call_ai = blocking_cnt
    capture.records.clear()
    r_a, _ = simulate("typical")
    time.sleep(0.5)                        # A's background run is now waiting for its AI answer
    r_b, dt_b = simulate("heavy_rain")
    check(r_a.status_code == 200 and r_b.status_code == 200, "both runs answered")
    check(dt_b < 5, f"run B is not blocked by run A's AI ({dt_b:.2f} s)")
    release.set()
    check(deferred.wait(1, 30), "background runs finish")
    time.sleep(0.2)
    notes = change_notes()
    texts = [summary(n) for n in notes]
    print("     " + " | ".join(f"#{n.id}: {s}" for n, (t, s) in zip(notes, texts)))
    check(len(notes) == 2, "two change notifications (A and B)")
    check(TEXT_A not in [t for t, _ in texts], "run A's late AI text was dropped (stale)")
    check(texts[0][1] == "rules", "run A's notification keeps its rule-based text")
    check(texts[-1] == (TEXT_B, "ai"), "run B's notification has run B's AI text")
    msgs = [rec.getMessage() for rec in capture.records]
    check(any("stale" in m for m in msgs), "stale run logged")

    # ── 3. failures are logged, the rule-based text stays ─────────────────────────────────
    print("\n-- the background work fails")
    reset_demo()
    capture.records.clear()
    orig_explain_job = deferred._explain_tasks

    def broken(*a, **k):
        raise RuntimeError("explanations broke")

    def failing_cnt(prompt):
        raise TimeoutError("AI down")

    deferred._explain_tasks = broken
    cnt._call_ai = failing_cnt
    r, _ = simulate("heavy_rain")
    check(deferred.wait(1, 30), "background run finishes")
    notes = change_notes()
    text, source = summary(notes[-1])
    check(r.status_code == 200 and source == "rules" and "unusual for May" in text,
          "AI down: the rule-based text stays")
    errors = [rec for rec in capture.records if rec.levelno >= logging.ERROR]
    check(any("task explanations failed" in rec.getMessage() for rec in errors), "job failure logged as an error")
    deferred._explain_tasks = orig_explain_job

    # ── 4. Reset demo makes running background work stale ─────────────────────────────────
    print("\n-- Reset demo while the AI is still writing")
    reset_demo()
    release = threading.Event()
    cnt._call_ai = lambda prompt: (release.wait(20), TEXT_A)[1]
    capture.records.clear()
    simulate("typical")
    time.sleep(0.5)
    rr = client.post("/mytasks/1/reset-demo")
    check(rr.status_code == 200, f"reset HTTP {rr.status_code}")
    release.set()
    check(deferred.wait(1, 30), "background run finishes")
    check(not any(TEXT_A in (n.detail or "") for n in Notification.query.all()), "no AI text written after the reset")
    reset_demo()

print(f"\n{'ALL PASSED' if not FAILED else f'{len(FAILED)} FAILED: {FAILED}'}")
sys.exit(1 if FAILED else 0)
