"""Decision recommendation when the AI is unavailable – forced HTTP 503s, no network.

Run from the project root with DEMO_TODAY=2027-05-05 USE_PLACEHOLDER_AI=true:
    python Test_Runs/test_recommendation_retry.py
The real GoogleAIProvider is used with a fake HTTP transport: the primary model always answers
HTTP 503; the fallback model answers (or also fails, per test step).
1. 503 on the primary → GOOGLE_AI_FALLBACK_MODEL answers → recommendation stored.
2. 503 on both → no recommendation, but nothing marks it as final (None, retried later);
   the notification shows the options.
3. The deferred AI run retries once after the delay (and a newer run makes the retry stale).
4. Opening the Decide task's details asks once (lazy, debounced).
"""
import io
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FAILED = []


def check(cond, label):
    print(f"  {'OK  ' if cond else 'FAIL'} {label}")
    if not cond:
        FAILED.append(label)


from run import app  # noqa: E402

PRIMARY, FALLBACK = "gemma-4-test-it", "fallback-test-lite"
REASON = ("The sowing window ends on 8 May, and no day left in it is suitable. Sowing on 9 May is the first "
          "suitable day in the forecast, with a harvest about 9 Oct.")
calls = []                 # (model, kind)
state = {"fallback_ok": True, "fail_fallback_n": 0}   # fail_fallback_n: the next N fallback calls fail


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def fake_urlopen(req, timeout=None):
    url = req.full_url if hasattr(req, "full_url") else str(req)
    if url.endswith("/models") or "/models?" in url:
        return _Resp(json.dumps({"models": [{"name": f"models/{PRIMARY}"}]}).encode())
    model = url.split("/models/")[1].split(":")[0]
    body = json.loads(req.data.decode())
    prompt = " ".join(p.get("text", "") for c in body.get("contents", []) for p in c.get("parts", []))
    prompt += " ".join(p.get("text", "") for p in (body.get("systemInstruction") or {}).get("parts", []))
    kind = "recommendation" if "sowing decision" in prompt else "other"
    calls.append((model, kind))
    fail_once = model == FALLBACK and kind == "recommendation" and state["fail_fallback_n"] > 0
    if fail_once:
        state["fail_fallback_n"] -= 1
    if model == PRIMARY or not state["fallback_ok"] or kind != "recommendation" or fail_once:
        raise urllib.error.HTTPError(url, 503, "Service Unavailable", {}, io.BytesIO(b"{}"))
    key = prompt.split("Decision ")[1].split(":")[0]
    text = json.dumps({key: {"option": "sow_anyway", "reason": REASON}})
    return _Resp(json.dumps({"candidates": [{"content": {"parts": [{"text": text}]}}]}).encode())


with app.app_context():
    from app.extensions import db
    from app.models.notification import Notification
    from app.models.task import Task
    from app.services import decision_recommendation_service as dr
    from app.services import deferred_ai_service as deferred
    from app.services.ai_model_service import ai_model_service
    from app.services.ai_model_service.Gemma import google_ai_provider as gp
    from app.services.demo_reset_service import reset_demo
    from app.utils import demo_flags

    demo_flags.simulator_wait_seconds = lambda uid: 0
    client = app.test_client()
    gp.urllib.request.urlopen = fake_urlopen
    provider = gp.GoogleAIProvider(api_key="test-key", model=PRIMARY, fallback_model=FALLBACK)
    placeholder_fast = ai_model_service._fast_provider

    def decision():
        db.session.expire_all()
        return Task.query.filter_by(user_id=1, task_type="decision").order_by(Task.id.desc()).first()

    def note():
        db.session.expire_all()
        return (Notification.query.filter_by(user_id=1, entity_type="seasonal_plan_entry")
                .order_by(Notification.id.desc()).first())

    def start_s3():
        reset_demo()
        client.post("/mytasks/1/run-weather-simulator", json={"scenario": "window_running_out"})
        deferred.wait(1, 60)

    # ── 1. primary 503 → fallback model ────────────────────────────────────────────────
    print("\n-- 1. HTTP 503 on the primary model → the fallback model answers")
    start_s3()                                     # placeholder: no model → "" (options)
    check(decision().ai_explanation == "", "placeholder provider: options only, not retried")
    ai_model_service._fast_provider = provider
    calls.clear()
    res = dr.recommend(1, include_dropped=True)
    d = decision()
    check(res["recommended"] == [d.id] and d.ai_explanation.startswith("Sow anyway with precautions."),
          f"recommendation stored ({res})")
    check(calls == [(PRIMARY, "recommendation"), (FALLBACK, "recommendation")], f"primary 503, then fallback {calls}")
    check(ai_model_service.answered_model() == FALLBACK, f"answered by the fallback ({ai_model_service.answered_model()})")
    check(f"{dr.LABEL}: Sow anyway with precautions." in note().detail, "notification shows it")

    # ── 2. 503 on both → None (to be retried), options shown ──────────────────────────
    print("\n-- 2. HTTP 503 on both models")
    d.ai_explanation = None
    db.session.commit()
    state["fallback_ok"] = False
    calls.clear()
    res = dr.recommend(1)
    d = decision()
    check(res["failed"] == [d.id] and d.ai_explanation is None, f"no recommendation, left for a retry ({d.ai_explanation!r})")
    check(calls == [(PRIMARY, "recommendation"), (FALLBACK, "recommendation")], f"both models tried {calls}")
    check(note().detail.endswith(dr.NO_RECOMMENDATION), "notification: the options + 'No AI recommendation'")
    r = client.get("/mytasks/tasks/pending")
    check(r.status_code == 200, "task list still loads")

    # ── 3. deferred retry after the delay ─────────────────────────────────────────────
    print("\n-- 3. the deferred AI run retries once after the delay")
    deferred.RECOMMEND_RETRY_DELAY_S = 1.0
    state["fallback_ok"] = True
    calls.clear()
    run = deferred.new_run(1)
    t0 = time.monotonic()
    deferred._recommend_retry(1, run, 0)
    dt = time.monotonic() - t0
    d = decision()
    check(dt >= 0.9 and d.ai_explanation and d.ai_explanation.startswith("Sow anyway"),
          f"retried after {dt:.1f} s → stored")
    print("   … end to end: the simulator's background run – first attempt 503 on both models, retry works")
    state["fallback_ok"], state["fail_fallback_n"] = True, 1
    deferred.RECOMMEND_RETRY_DELAY_S = 1.0
    reset_demo()
    calls.clear()
    t0 = time.monotonic()
    client.post("/mytasks/1/run-weather-simulator", json={"scenario": "window_running_out"})
    deferred.wait(1, 60)
    rec_calls = [m for m, k in calls if k == "recommendation"]
    d = decision()
    print(f"     recommendation calls: {rec_calls} ({time.monotonic() - t0:.1f} s)")
    check(rec_calls == [PRIMARY, FALLBACK, PRIMARY, FALLBACK], "attempt 1: primary + fallback 503; retry: primary 503, fallback ok")
    check(d.ai_explanation and d.ai_explanation.startswith("Sow anyway"), "stored by the run's own retry")
    check(f"{dr.LABEL}: Sow anyway" in note().detail, "notification updated by the retry")
    print("   … a newer run makes the waiting retry stale")
    d.ai_explanation = None
    db.session.commit()
    deferred.RECOMMEND_RETRY_DELAY_S = 3.0
    calls.clear()
    run = deferred.new_run(1)

    def bg():
        with app.app_context():
            deferred._recommend_retry(1, run, 0)
            db.session.remove()
    th = threading.Thread(target=bg)
    th.start()
    time.sleep(0.5)
    deferred.new_run(1)                             # e.g. Reset demo / another simulator click
    th.join(10)
    check(not [c for c in calls if c[1] == "recommendation"] and decision().ai_explanation is None,
          "stale: no retry call, nothing written")

    # ── 4. lazy, debounced when the details are opened ───────────────────────────────
    print("\n-- 4. opening the Decide task's details")
    dr._lazy_last.clear()
    state["fallback_ok"] = False
    d = decision()
    calls.clear()
    r1 = client.post(f"/mytasks/1/decision/{d.id}/recommendation").get_json()
    n1 = len([c for c in calls if c[1] == "recommendation"])
    r2 = client.post(f"/mytasks/1/decision/{d.id}/recommendation").get_json()
    n2 = len([c for c in calls if c[1] == "recommendation"])
    check(r1["status"] == "failed" and n1 == 2, f"first open: one call (primary + fallback), failed ({r1['status']}, {n1})")
    check(r2["status"] == "debounced" and n2 == n1, "opened again at once: debounced, no call")
    dr._lazy_running.add(d.id)
    r3 = client.post(f"/mytasks/1/decision/{d.id}/recommendation").get_json()
    dr._lazy_running.discard(d.id)
    check(r3["status"] == "in_progress", "while a call runs: in progress, no second call")
    state["fallback_ok"] = True
    dr._lazy_last.clear()                           # the debounce interval has passed
    r4 = client.post(f"/mytasks/1/decision/{d.id}/recommendation").get_json()
    check(r4["status"] == "recommended" and r4["text"].startswith("Sow anyway"), f"AI back: recommended ({r4['status']})")
    r5 = client.post(f"/mytasks/1/decision/{d.id}/recommendation").get_json()
    check(r5["status"] == "stored", "afterwards: the stored text, no call")

    ai_model_service._fast_provider = placeholder_fast
    reset_demo()

print(f"\n{'ALL PASSED' if not FAILED else f'{len(FAILED)} FAILED: {FAILED}'}")
sys.exit(1 if FAILED else 0)
