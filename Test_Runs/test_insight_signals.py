"""Signals for task insights / farm report (Step G.2) — no AI.

Run from the project root with DEMO_TODAY=2027-05-05 USE_PLACEHOLDER_AI=true:
    python Test_Runs/test_insight_signals.py
Reseeds the local DB (like a server start), runs the simulator's daily update for 5 May 2027
and checks that the signals carry the demo's expected cases with valid sources.
"""
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FAILED = []


def check(cond, label):
    print(f"  {'OK  ' if cond else 'FAIL'} {label}")
    if not cond:
        FAILED.append(label)


def find(signals, kind, *words):
    return [s for s in signals if s["kind"] == kind and all(w.lower() in s["text"].lower() for w in words)]


# ── 1. Date guard ──────────────────────────────────────────────────────────────
from app.utils.date_guard import dates_in, dates_outside  # noqa: E402

print("\n-- date guard")
for text, want in [("showers 7–8 May", {(7, 5), (8, 5)}), ("on 7 and 8 May", {(7, 5), (8, 5)}),
                   ("May 7-8", {(7, 5), (8, 5)}), ("8 May 4 mm", {(8, 5)}), ("30–40 °C, 4–8 h", set()),
                   ("harvest 7 Oct → 9 Oct", {(7, 10), (9, 10)}), ("on May 9th", {(9, 5)})]:
    check(set(dates_in(text)) == want, f"dates_in({text!r}) = {sorted(want)}")
check(dates_outside("showers 6–8 May", [date(2027, 5, 7), date(2027, 5, 8)]) == [(6, 5)],
      "dates_outside: 6 May of '6–8 May' is not in the allowed 7–8 May")

# ── 2. Demo state (user 1, 5 May 2027, after the simulator's daily update) ─────
from run import app  # noqa: E402  bootstrap(): fresh reseed

with app.app_context():
    from app.agents.coordinator_agent import CoordinatorAgent
    from app.models.task import Task
    from app.services import insight_signals_service as sig
    from app.utils import clock

    today = clock.today()
    print(f"\n-- user 1 on {today}")
    from app.services import demo_scenario_service
    demo_scenario_service.apply(1, "typical")   # scenario 1: 7–8 May western disturbance
    CoordinatorAgent().daily_update(user_id=1, as_of_date=today)
    signals = sig.build_signals(1)
    for s in signals:
        print(f"     [{s['id']}] {s['kind']}: {s['text'][:150]}")
    pending = {t.id: t for t in Task.query.filter_by(user_id=1, completed=False, is_active=True)}
    title = lambda tid: pending[tid].title if tid in pending else "?"

    # Expected case 1: erosion on The Reservoir before cotton sowing on 9 May
    dep = find(signals, "dependency", "The Reservoir", "9 May", "Erosion")
    check(dep and any(e["event"] == "sowing" and e["date"] == "2027-05-09" and e["crop"] == "Cotton"
                      for e in dep[0]["sources"]["plan_events"])
          and any("Erosion" in title(t) for t in dep[0]["sources"]["tasks"]),
          "dependency: erosion task on The Reservoir before Cotton sowing 9 May")

    # Expected case 2: showers 7–8 May vs soil work
    rain = find(signals, "weather", "Showers", "7–8 May")
    check(rain and rain[0]["sources"]["forecast_days"] == ["2027-05-07", "2027-05-08"]
          and any("Erosion" in title(t) for t in rain[0]["sources"]["tasks"])
          and any("seedbed" in title(t).lower() for t in rain[0]["sources"]["tasks"]),
          "weather: showers 7–8 May with the pending soil work before them")

    # Expected case 3: maize sowing tomorrow vs seedbed check today
    dl = find(signals, "deadline", "Maize", "tomorrow")
    dl_titles = [title(t).lower() for t in dl[0]["sources"]["tasks"]] if dl else []
    check(dl and any("seedbed" in t for t in dl_titles) and any("check soil" in t for t in dl_titles)
          and dl[0]["sources"]["plan_events"][0]["date"] == "2027-05-06",
          "deadline: Sow Maize tomorrow (6 May) with today's seedbed + soil check tasks")

    # Expected case 4: Rice Not Feasible, no tasks
    nf = find(signals, "plan_change", "Rice", "Not Feasible")
    check(nf and not nf[0]["sources"]["tasks"] and "no tasks" in nf[0]["text"],
          "plan_change: Rice Not Feasible, no tasks")

    moved = find(signals, "plan_change", "Cotton", "moved from 7 May to 9 May")
    check(moved and "harvest 7 Oct → 9 Oct" in moved[0]["text"], "plan_change: Cotton sowing 7 → 9 May + cascades")
    check(find(signals, "load", "Busiest day: 5 May"), "load: busiest day 5 May")
    check(len(find(signals, "field_status")) == 3, "field_status: one per active field (3)")

    # Consistency
    ids = [s["id"] for s in signals]
    check(ids == [f"S{i}" for i in range(1, len(ids) + 1)], "ids S1..Sn in order")
    check(len({s["key"] for s in signals}) == len(signals), "keys unique")
    check(all({f"{date(today.year, m, d)}" for d, m in dates_in(s["text"])} <= set(s["dates"]) for s in signals),
          "every date in a text is in the signal's dates")
    check(all(t in pending for s in signals for t in s["sources"]["tasks"]), "task sources are pending tasks")
    check(all(s["labels"] for s in signals), "every signal has evidence labels")
    check([s["severity"] for s in signals] == sorted(s["severity"] for s in signals), "most urgent first")
    again = sig.build_signals(1)
    check([(s["key"], s["text"]) for s in again] == [(s["key"], s["text"]) for s in signals],
          "same data → same signals")

    for uid in (2, 3):
        CoordinatorAgent().daily_update(user_id=uid, as_of_date=today)
        other = sig.build_signals(uid)
        check(other and all(s["text"] for s in other), f"user {uid}: {len(other)} signals, no errors")

    # ── 3. Made-up snapshot: kinds the demo day doesn't have ──────────────────
    print("\n-- made-up snapshot (overdue, decision needed, heat)")
    d0 = date(2027, 5, 5)
    t = lambda i, ttl, pr, due, typ="inspection", cat="field", fid=1: {
        "id": i, "title": ttl, "priority": pr, "due": due, "type": typ, "category": cat,
        "field_id": fid, "field": "F1", "crop": None, "entry_id": None}
    snap = {
        "today": d0,
        "tasks": [t(1, "Old check", "high", d0 - timedelta(days=2)), t(2, "Irrigate", "medium", d0 + timedelta(days=1),
                                                                      "irrigation")],
        "events": [],
        "entries": [{"entry_id": 9, "crop": "Cotton", "crop_name_id": 3, "field_id": 1, "field": "F1",
                     "feasibility": "Ideal", "not_feasible_reason": None, "sowing_status": "decision_needed",
                     "sowing_note": "No suitable sowing day in the window", "dry_note": None, "moved": [],
                     "sowing_done_on": None}],
        "forecast": [{"date": d0 + timedelta(days=i), "temp": 37.0 if i in (1, 2) else 30.0, "rain": 0.0,
                      "sun": 11, "humidity": 30} for i in range(7)],
        "fields": [],
    }
    made = sig.build_from(snap)
    check(find(made, "load", "1 overdue task", "Old check"), "overdue task → load signal")
    check(find(made, "plan_change", "Decision needed", "Cotton") and
          find(made, "plan_change", "Decision needed")[0]["severity"] == 1, "decision needed → severity 1")
    heat = find(made, "weather", "Heat on 6–7 May")
    check(heat and heat[0]["sources"]["tasks"] == [2], "heat 6–7 May with the irrigation task due then")

print(f"\n{'ALL PASSED' if not FAILED else f'{len(FAILED)} FAILED: {FAILED}'}")
sys.exit(1 if FAILED else 0)
