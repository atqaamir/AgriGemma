"""Real-AI check of plan task explanations (4 cases, two batched AI calls).

    DEMO_TODAY=2027-05-05 python Test_Runs/plan_task_explanation_eval.py [--out file.json]

Cases: Sow Maize 6 May (planned date, suitable), Sow Cotton 9 May (moved by the sowing window),
a regular irrigation on 13 May and an extra dry-week irrigation on 14 May (Maize sown 6 May).
Each explanation must name the actual reason (keywords) and no date other than the due date
(the date guard drops those; drops are reported).
"""
import argparse
import json
import logging
import os
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
logging.disable(logging.CRITICAL)
assert os.getenv("DEMO_TODAY") == "2027-05-05", "run with DEMO_TODAY=2027-05-05"

CASES = [
    # (label, title prefix, due date, reason keywords: any must appear)
    ("Sow Maize, planned date", "Sow Maize", date(2027, 5, 6), [r"planned", r"suitable", r"temperature", r"warm"]),
    ("Sow Cotton, moved by the sowing window", "Sow Cotton", date(2027, 5, 9),
     [r"sunlight", r"sunshine", r"cloud", r"temperature", r"first suitable", r"days before", r"earlier"]),
    ("Irrigation, regular session", "Irrigate Maize", date(2027, 5, 13), [r"regular", r"schedul", r"start"]),
    ("Irrigation, extra dry-week session", "Irrigate Maize", date(2027, 5, 14), [r"dry", r"rain", r"extra"]),
]


def main():
    import re
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    from app.services import plan_task_explanation_service as ex
    real_call = ex._call_ai
    no_ai = lambda prompt, facts: "{}"                 # daily updates in the setup: no AI call
    ex._call_ai = no_ai

    import run  # noqa: F401  reseed on 5 May 2027
    from app.extensions import db
    from app.agents.coordinator_agent import CoordinatorAgent
    from app.models.task import Task
    from app.models.weather_forecast import WeatherForecast
    from app.services.ai_model_service import ai_model_service
    from app.services.domain_service.task_service import TaskService
    from app.services.task_generation_service import TaskGenerationService
    from app.utils import clock
    from Test_Runs.seed_data import seed_demo_weather

    with run.app.app_context():
        # 5 May: plan with Maize sowing 6 May and Cotton moved to 9 May (7–8 May unsuitable)
        CoordinatorAgent().daily_update(user_id=1, as_of_date=clock.today())
        sow_cotton = TaskGenerationService.generate_plan_tasks(1, date(2027, 5, 9))["created"]
        maize = Task.query.filter(Task.title.like("Sow Maize%")).first()
        for t in [maize] + sow_cotton:
            t.ai_explanation = None
        db.session.commit()
        ex._call_ai = real_call                         # real call 1: Sow Maize + Sow Cotton
        batches = [ex.explain(1, [maize] + sow_cotton)]
        ex._call_ai = no_ai
        # Maize sown 6 May → irrigation from 13 May; plan as of 8 May (window 8–14 May)
        os.environ["DEMO_TODAY"] = "2027-05-06"
        TaskService.update_task(maize.id, {"completed": True})
        seed_demo_weather(start=date(2027, 5, 12))      # 12–18 May; keeps 5–11 May
        dry = WeatherForecast.query.filter_by(region="Punjab, Pakistan", date=date(2027, 5, 14)).first()
        dry.avg_temperature_c, dry.rainfall_mm, dry.sunlight_hours, dry.humidity = 32.5, 0.0, 10.4, 30
        db.session.commit()
        os.environ["DEMO_TODAY"] = "2027-05-08"
        CoordinatorAgent().daily_update(user_id=1, as_of_date=clock.today())
        irrigation = []
        for d in (date(2027, 5, 13), date(2027, 5, 14)):
            irrigation += TaskGenerationService.generate_plan_tasks(1, d)["created"]
        irrigation += Task.query.filter(Task.title.like("Irrigate Maize%"),
                                        Task.due_date.in_([date(2027, 5, 13), date(2027, 5, 14)])).all()
        for t in irrigation:
            t.ai_explanation = None
        db.session.commit()
        ex._call_ai = real_call                         # real call 2: the two irrigation tasks
        batches.append(ex.explain(1, irrigation))
        provider = (ai_model_service._fast_provider or ai_model_service.get_provider()).name
        result = {k: sum((b[k] for b in batches if isinstance(b[k], list)), []) for k in ("explained", "dropped", "failed")}
        result["calls"] = sum(1 for b in batches if b["called"])
        db.session.expire_all()

        rows, ok_all = [], True
        print(f"plan task explanation eval: provider {provider}; batch {result}")
        for label, prefix, due, keywords in CASES:
            t = (Task.query.filter(Task.title.like(prefix + "%"), Task.due_date == due, Task.user_id == 1)
                 .order_by(Task.id.desc()).first())
            text = (t.ai_explanation if t else None) or ""
            dropped = bool(t) and t.id in result["dropped"]
            reason = any(re.search(k, text, re.I) for k in keywords)
            other_date = ex.mentions_other_date(text, due) if text else False
            ok = bool(text) and reason and not other_date
            ok_all &= ok
            rows.append({"case": label, "task": t.title if t else None, "due": due.isoformat(),
                         "explanation": text, "names_reason": reason, "other_date": other_date,
                         "dropped": dropped, "description": t.description if t else None, "ok": ok})
            print(f"\n[{'OK' if ok else 'FAIL'}] {label} — {t.title if t else 'TASK MISSING'} ({due})"
                  f"\n   reason named: {reason}; other date: {other_date}; dropped by guard: {dropped}"
                  f"\n   explanation: {text or '(empty)'}\n   description: {t.description if t else ''}")
        print(f"\n{'ALL OK' if ok_all else 'NOT ALL OK'}")
        if args.out:
            Path(args.out).write_text(json.dumps({"provider": provider, "batch": result, "rows": rows},
                                                 ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
