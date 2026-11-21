"""To-do list "Recommended order": stored task insights when fresh (with each task's reason),
otherwise the rule-based order – never an AI call; priorities unchanged. Placeholder provider.

Run from the project root with DEMO_TODAY=2027-05-05 USE_PLACEHOLDER_AI=true:
    python Test_Runs/test_recommended_order.py
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

with app.app_context():
    from app.extensions import db
    from app.models.task import Task
    from app.services import task_insights_service as ti
    from app.services.ai_model_service import ai_model_service
    from app.services.domain_service.task_service import TaskService
    from app.utils import clock

    client = app.test_client()
    today = clock.today()
    calls = []
    for name in ("complete", "stream_complete", "fast_complete", "fast_complete_json", "fast_complete_direct"):
        orig = getattr(ai_model_service, name)
        setattr(ai_model_service, name, lambda *a, _o=orig, _n=name, **k: (calls.append(_n), _o(*a, **k))[1])
    orig_ti_call = ti._call_with_limit
    ti_calls = []
    ti._call_with_limit = lambda *a, **k: (ti_calls.append(1), orig_ti_call(*a, **k))[1]

    def priorities():
        db.session.expire_all()
        return {t.id: t.priority for t in Task.query.filter_by(user_id=1).all()}

    def get():
        r = client.get("/mytasks/recommended-order?user_id=1")
        return r.status_code, r.get_json() or {}

    before = priorities()

    print("\n-- no stored insights: rule-based order")
    st, body = get()
    order = body.get("order") or []
    check(st == 200 and body.get("source") == "rules" and order, f"HTTP {st}, source {body.get('source')}")
    pending = {t.id: t for t in Task.query.filter(Task.user_id == 1, Task.completed.is_(False),
                                                   Task.is_active.is_(True)).all()}
    ids = [o["task_id"] for o in order]
    due = [max(pending[i].due_date, today) for i in ids]
    check(all(pending[i].due_date <= today.replace(day=today.day + 1) for i in ids), "only today's / tomorrow's tasks")
    check(due == sorted(due), "today's before tomorrow's")
    rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    same_day = [[rank[pending[i].priority] for i, d in zip(ids, due) if d == day] for day in sorted(set(due))]
    check(all(x == sorted(x) for x in same_day), "within a day: priority order")
    check(all(o["reason"] and o["source"] == "rule" for o in order), "every task has a one-line reason")
    print("     " + " | ".join(f"#{o['task_id']} {o['reason']}" for o in order[:3]))
    check(not calls and not ti_calls, f"no AI call ({calls}, {ti_calls})")

    print("\n-- fresh stored insights: their order and reasons")
    stored = ti.generate(1)
    n_calls = len(ti_calls)
    st, body = get()
    want = [(x["task_id"], x["reason"]) for x in stored["data"]["priority_order"]]
    got = [(o["task_id"], o["reason"]) for o in body["order"]]
    check(body.get("source") == "insights" and body.get("stale") is False and got == want,
          f"source insights, same order and reasons ({len(got)} tasks)")
    check(len(ti_calls) == n_calls, "reading the order makes no AI call")

    print("\n-- the farm changes: stale → rule-based again")
    first = next(i for i in ids if pending[i].due_date == today)
    TaskService.update_task(first, {"completed": True})
    st, body = get()
    check(body.get("source") == "rules" and body.get("stale") is True, f"source {body.get('source')}, stale {body.get('stale')}")
    check(first not in [o["task_id"] for o in body["order"]], "the completed task is no longer in the order")
    check(len(ti_calls) == n_calls, "still no AI call")

    after = priorities()
    check(all(after[i] == before[i] for i in before), "priorities unchanged")

print(f"\n{'ALL PASSED' if not FAILED else f'{len(FAILED)} FAILED: {FAILED}'}")
sys.exit(1 if FAILED else 0)
