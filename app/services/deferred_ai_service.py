"""AI texts after a simulator run, in the background.

The simulator request returns as soon as the plan and the tasks are updated; the notifications
are created with their rule-based text. Then a background thread (own app context):
  1. "Why" texts for the plan tasks that have none (plan_task_explanation_service.explain);
  2. the change notification summary (change_notification_text.ai_text) → replaces the
     rule-based text in the alert detail and the change pop-up's report.

Runs are numbered per user. A newer simulator run (or Reset demo) makes older background work
stale. The request holds the user's write lock while it starts a run and updates the plan
(foreground()); background work checks is_current() and commits under the same lock
(current_write()), so stale results are dropped and never overwrite a newer run. One
background run per user at a time. Failures are logged, never raised; the rule-based texts stay.
"""
from __future__ import annotations

import json
import logging
import threading
import time
from collections import defaultdict
from contextlib import contextmanager

logger = logging.getLogger(__name__)

_state_lock = threading.Lock()
_runs: dict[int, int] = defaultdict(int)
_user_locks: dict[int, threading.Lock] = defaultdict(threading.Lock)
_threads: dict[int, threading.Thread] = {}
_write_locks: dict[int, threading.Lock] = defaultdict(threading.Lock)


def new_run(user_id: int) -> int:
    """Start a new run for the user: older background work becomes stale."""
    with _state_lock:
        _runs[user_id] += 1
        return _runs[user_id]


def is_current(user_id: int, run: int) -> bool:
    with _state_lock:
        return _runs[user_id] == run


def invalidate_all() -> None:
    """Reset demo: every user's running background work becomes stale."""
    with _state_lock:
        users = list(_runs)
    for uid in users:
        with _write_locks[uid]:
            new_run(uid)


@contextmanager
def foreground(user_id: int):
    """The request's part: a new run number, and the plan update under the write lock.
    Yields the run number."""
    with _write_locks[user_id]:
        yield new_run(user_id)


@contextmanager
def current_write(user_id: int, run: int):
    """Background writes: yields True if this run is still the latest; the request cannot
    start a newer run until the block ends (check + commit together)."""
    with _write_locks[user_id]:
        yield is_current(user_id, run)


def start(app, user_id: int, run: int, first_notification_id: int) -> threading.Thread:
    """Run the AI texts for this run in a background thread."""
    t = threading.Thread(target=_work, args=(app, user_id, run, first_notification_id),
                         name=f"deferred-ai-u{user_id}-r{run}", daemon=True)
    with _state_lock:
        _threads[user_id] = t
    t.start()
    return t


def wait(user_id: int, timeout: float = 60.0) -> bool:
    """Tests: wait for the user's latest background run. True if it finished."""
    with _state_lock:
        t = _threads.get(user_id)
    if t is None:
        return True
    t.join(timeout)
    return not t.is_alive()


def _work(app, user_id: int, run: int, first_notification_id: int) -> None:
    with _user_locks[user_id]:                     # one background run per user at a time
        if not is_current(user_id, run):
            logger.info("Deferred AI user=%s run=%s: stale before start – skipped", user_id, run)
            return
        with app.app_context():
            from app.extensions import db
            t0 = time.monotonic()
            for name, job in (("task explanations", _explain_tasks), ("change notification", _fill_notifications)):
                try:
                    job(user_id, run, first_notification_id)
                except Exception:
                    db.session.rollback()
                    logger.exception("Deferred AI user=%s run=%s: %s failed – rule-based text stays",
                                     user_id, run, name)
            db.session.remove()
            logger.info("Deferred AI user=%s run=%s done in %.1f s", user_id, run, time.monotonic() - t0)


def _explain_tasks(user_id: int, run: int, _first_id: int) -> None:
    from app.services import plan_task_explanation_service as explanations
    result = explanations.explain(user_id, [], write_guard=lambda: current_write(user_id, run))
    logger.info("Deferred AI user=%s run=%s: task explanations %s", user_id, run, result)


def _fill_notifications(user_id: int, run: int, first_id: int) -> None:
    from app.extensions import db
    from app.models.notification import Notification
    from app.services import change_notification_text as cnt
    from app.services.domain_service.notification_service import NotificationService
    from app.services.intelligence_service.context.context_builder import build_notification_context

    notes = (Notification.query.filter(Notification.user_id == user_id, Notification.id >= first_id,
                                       Notification.notification_type.in_(("change", "alert", "warning")))
             .order_by(Notification.id).all())
    if not notes:
        return
    task_summaries, _ = NotificationService._collect_change_data(user_id)
    farmer = build_notification_context(user_id).get("farmer_name") or "Farmer"
    facts = cnt.facts(user_id, task_summaries, farmer)
    text, source = cnt.ai_text(user_id, facts)
    if source != "ai":
        logger.info("Deferred AI user=%s run=%s: no usable AI summary – rule-based text stays", user_id, run)
        return
    with current_write(user_id, run) as current:
        if not current:                              # a newer run started while the AI was writing
            logger.info("Deferred AI user=%s run=%s: stale – AI summary dropped", user_id, run)
            db.session.rollback()
            return
        for n in notes:
            if n.notification_type == "change":
                try:
                    report = json.loads(n.detail or "{}")
                except ValueError:
                    continue
                report["ai_summary"] = text
                report["ai_summary_source"] = "ai"
                n.detail = json.dumps(report, ensure_ascii=False)
            else:
                n.detail = text
        db.session.commit()
    logger.info("Deferred AI user=%s run=%s: AI summary written to notifications %s",
                user_id, run, [n.id for n in notes])
