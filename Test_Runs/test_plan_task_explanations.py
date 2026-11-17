"""Plan task explanations: date guard (unit) and batching / failures / self-healing (runs).

Run from the project root with DEMO_TODAY=2027-05-05 USE_PLACEHOLDER_AI=true:
    python Test_Runs/test_plan_task_explanations.py
The AI call is replaced by a stub that counts calls and can fail, time out or answer badly.
"""
import json
import logging
import os
import sys
import time
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
logging.disable(logging.CRITICAL)
assert os.getenv("DEMO_TODAY") == "2027-05-05", "run with DEMO_TODAY=2027-05-05"

from app.services import plan_task_explanation_service as ex  # noqa: E402

failures = []


def check(cond, label):
    print(f"  {'OK  ' if cond else 'FAIL'} {label}")
    if not cond:
        failures.append(label)


# ── 1. date guard ──────────────────────────────────────────────────────────────
print("== date guard")
due = date(2027, 5, 9)
for text in ("Sowing moved to 10 May.", "May 10 was too cloudy.", "the 10th May", "on 10/05",
             "on 2027-05-10", "7 and 8 May were unsuitable"):
    check(ex.mentions_other_date(text, due), f"other date found: {text!r}")
for text in ("Sow on 9 May.", "Sunday, May 9", "the 9th May", "09/05", "2027-05-09",
             "rain under 50 mm", "30–40 °C and sunlight >8 h", "10.5 h of sun", "humidity 30 %",
             "4–8 h of sun on the days before", "stress low, 28 out of 100"):
    check(not ex.mentions_other_date(text, due), f"no other date: {text!r}")

# ── stubbed AI ─────────────────────────────────────────────────────────────────
STUB = {"mode": "ok", "calls": 0, "batch": []}


def stub(prompt, facts):
    STUB["calls"] += 1
    STUB["batch"] = [f["task_id"] for f in facts]
    mode = STUB["mode"]
    if mode == "fail":
        raise RuntimeError("AI down")
    if mode == "slow":
        time.sleep(ex.TIMEOUT_S + 2)
    if mode == "bad":
        return "not json"
    if mode == "otherdate":
        return json.dumps({str(f["task_id"]): "Moved from 7 May because of clouds." for f in facts})
    return json.dumps({str(f["task_id"]): f"Because of the rule ({f.get('rule', f['event'])}), on "
                       f"{f['due_date']}." for f in facts})


ex._call_ai = stub

import run  # noqa: E402  fresh reseed on 5 May 2027
from app.extensions import db  # noqa: E402
from app.agents.coordinator_agent import CoordinatorAgent  # noqa: E402
from app.models.task import Task  # noqa: E402
from app.models.weather import Weather  # noqa: E402
from app.models.weather_forecast import WeatherForecast  # noqa: E402
from app.services.domain_service.task_service import TaskService  # noqa: E402
from app.services.task_generation_service import TaskGenerationService  # noqa: E402
from app.utils import clock  # noqa: E402
from Test_Runs.seed_data import seed_demo_weather  # noqa: E402

for name in ("apscheduler", "werkzeug", "app"):
    logging.getLogger(name).setLevel(logging.CRITICAL)

T0 = date(2027, 5, 5)
D = lambda n: T0 + timedelta(days=n)
GOOD, BAD = (33.0, 10.5), (27.5, 5.5)


def set_day(n):
    os.environ["DEMO_TODAY"] = D(n).isoformat()


def set_weather(as_of, days):
    seed_demo_weather(start=as_of)
    for off, (temp, sun) in days.items():
        r = WeatherForecast.query.filter_by(region="Punjab, Pakistan", date=as_of + timedelta(days=off)).first()
        r.avg_temperature_c, r.sunlight_hours = temp, sun
    db.session.commit()


def run_daily(label, mode="ok"):
    STUB["mode"], before = mode, STUB["calls"]
    t0 = time.time()
    pt = CoordinatorAgent().daily_update(user_id=1, as_of_date=clock.today())["plan_tasks"]
    calls = STUB["calls"] - before
    e = pt.get("explanations", {})
    print(f"\n-- {label}: AI calls {calls}, batch {STUB['batch'] if calls else []}, "
          f"created {pt['created']}, moved {pt['moved']}, explained {e.get('explained')}, "
          f"failed {e.get('failed')}, dropped {e.get('dropped')}  ({time.time() - t0:.1f} s)")
    return calls, pt


def task(prefix):
    db.session.expire_all()
    return Task.query.filter(Task.title.like(prefix + "%"), Task.user_id == 1).order_by(Task.id.desc()).first()


with run.app.app_context():
    print("\n== runs (stubbed AI)")
    set_day(0)
    calls, _ = run_daily("5 May: new 'Sow Maize'")
    t = task("Sow Maize")
    check(calls == 1 and bool(t.ai_explanation), "new plan task explained, 1 call")
    print(f"     explanation: {t.ai_explanation!r}\n     description: {t.description!r}")

    calls, _ = run_daily("5 May again: nothing changed")
    check(calls == 0, "unchanged sync: 0 AI calls")

    set_day(1)
    set_weather(D(1), {0: GOOD, 1: GOOD, 2: BAD, 3: GOOD, 4: GOOD, 5: GOOD, 6: GOOD})
    calls, _ = run_daily("6 May: 7 May good → 'Sow Cotton' 7 May")
    cotton = task("Sow Cotton")
    first = cotton.ai_explanation
    check(calls == 1 and bool(first), "Sow Cotton explained (1 call)")

    set_weather(D(1), {0: GOOD, 1: BAD, 2: BAD, 3: GOOD, 4: GOOD, 5: GOOD, 6: GOOD})
    calls, _ = run_daily("6 May: 7–8 May bad → Cotton moved to 9 May")
    cotton = task("Sow Cotton")
    check(calls == 1 and cotton.due_date == D(4) and cotton.ai_explanation and cotton.ai_explanation != first,
          "moved task gets a new explanation (1 call)")
    print(f"     explanation: {cotton.ai_explanation!r}")

    set_weather(D(1), {0: GOOD, 1: GOOD, 2: BAD, 3: GOOD, 4: GOOD, 5: GOOD, 6: GOOD})
    calls, _ = run_daily("6 May: forecast improves, AI DOWN → Cotton back to 7 May", mode="fail")
    cotton = task("Sow Cotton")
    check(calls == 1 and cotton.due_date == D(2) and cotton.ai_explanation is None
          and cotton.description.startswith("From the weekly plan"),
          "AI failure: task moved, template description kept, explanation empty, no crash")
    calls, _ = run_daily("6 May: same plan, AI back → self-healing")
    cotton = task("Sow Cotton")
    check(calls == 1 and bool(cotton.ai_explanation) and cotton.id in STUB["batch"],
          "next run fills the empty explanation (1 call)")

    set_weather(D(1), {0: GOOD, 1: BAD, 2: BAD, 3: GOOD, 4: GOOD, 5: GOOD, 6: GOOD})
    calls, _ = run_daily("6 May: Cotton to 9 May, AI TIMEOUT", mode="slow")
    cotton = task("Sow Cotton")
    check(calls == 1 and cotton.ai_explanation is None, f"timeout after {ex.TIMEOUT_S:.0f} s: explanation empty")
    calls, _ = run_daily("6 May: AI answers without JSON", mode="bad")
    check(calls == 1 and task("Sow Cotton").ai_explanation is None, "bad answer: explanation empty")
    calls, _ = run_daily("6 May: AI names another date", mode="otherdate")
    cotton = task("Sow Cotton")
    check(calls == 1 and cotton.ai_explanation == ex.DROPPED, "other date: explanation dropped")
    calls, _ = run_daily("6 May: nothing changed after a drop")
    check(calls == 0, "a dropped explanation is not retried every run (0 calls)")

    # Maize sown 6 May → irrigation from 13 May; on 13 May: regular 13 May + extra 14 May
    sow_maize = task("Sow Maize")
    TaskService.update_task(sow_maize.id, {"completed": True})
    set_day(8)
    seed_demo_weather(start=D(8))
    calls, pt = run_daily("13 May: two new irrigation tasks in one run")
    irr = Task.query.filter(Task.title.like("Irrigate Maize%"), Task.due_date.in_([D(8), D(9)])).all()
    check(calls == 1 and len(irr) >= 2 and all(t.ai_explanation for t in irr), "2+ new tasks: one batched call")
    for t in sorted(irr, key=lambda x: x.due_date):
        print(f"     {t.due_date}: description {t.description!r}")
    extra = next((t for t in irr if t.due_date == D(9)), None)
    check(extra is not None and "Extra session: Dry week" in (extra.description or ""),
          "extra irrigation: description names the rule")

    print("\n== 7 PM job")
    before = STUB["calls"]
    r = TaskGenerationService().generate_daily_tasks(1)
    check(STUB["calls"] - before <= 1, f"7 PM job: at most 1 explanation call ({STUB['calls'] - before})")

print(f"\n{'ALL PASSED' if not failures else 'FAILED: ' + str(failures)}")
