"""Storage and staleness for the AI insight results (task insights, farm report).

A report stores the signals it was built from and a fingerprint of the farm data:
  date  – the demo date (a new day changes what "today" / "tomorrow" mean)
  tasks – each task's id, title, due date, priority, type, field, done, active
          (not ai_explanation / description: an explanation filled in later is no change)
  plan  – the active weekly plan's window, per entry its sowing status and events, and the
          plan overrides (planned vs actual dates). Ids and generated_at are left out, so a
          same-day simulator rerun that produces the same plan is no change.
Reading a report never calls the AI; if the fingerprint differs the page shows "Your farm
changed since this report – regenerate?".
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import date, datetime, timezone

from app.extensions import db
from app.models.ai_insight_report import AiInsightReport
from app.utils import clock

logger = logging.getLogger(__name__)

KINDS = ("task_insights", "farm_report")
CHANGED_BANNER = "Your farm changed since this report – regenerate?"


def _hash(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def fingerprint_parts(user_id: int, today: date | None = None) -> dict:
    """{"date": ISO, "tasks": hash, "plan": hash} of the data the reports are based on."""
    from app.models.task import Task
    from app.models.seasonal_plan import SeasonalPlan
    from app.models.plan_event_override import PlanEventOverride
    from app.repositories.weekly_plan_repository import WeeklyPlanRepository

    today = today or clock.today()
    tasks = [(t.id, t.title, t.due_date, t.priority, t.task_type, t.field_id, bool(t.completed), bool(t.is_active))
             for t in Task.query.filter_by(user_id=user_id).order_by(Task.id).all()]

    plan_rows = []
    weekly = WeeklyPlanRepository.get_active_by_user_id(user_id)
    if weekly:
        plan_rows.append(("window", weekly.week_start_date, weekly.week_end_date))
        for e in sorted(weekly.entries, key=lambda x: (x.crop_id, x.field_id or 0)):
            events = json.loads(e.week_events or "[]")
            adjustments = json.loads(e.climate_adjustments or "[]")
            status = next((a.get("status") for a in adjustments if a.get("factor") == "sowing_window"), None)
            plan_rows.append(("entry", e.crop_id, e.field_id, status,
                              sorted((x.get("event_type"), x.get("date"), bool(x.get("extra"))) for x in events)))
    seasonal = SeasonalPlan.query.filter_by(user_id=user_id, currently_active=True).first()
    if seasonal:
        entry_ids = [e.id for e in seasonal.entries]
        plan_rows += sorted(("override", o.seasonal_plan_entry_id, o.event_type, o.actual_date, o.source, o.as_of_date)
                            for o in PlanEventOverride.query.filter(
                                PlanEventOverride.seasonal_plan_entry_id.in_(entry_ids)).all())
        plan_rows += sorted(("feasibility", e.id, e.feasibility) for e in seasonal.entries)
    return {"date": today.isoformat(), "tasks": _hash(tasks), "plan": _hash(plan_rows)}


def fingerprint(parts: dict) -> str:
    return _hash(parts)


def save(user_id: int, kind: str, data: dict, signals: list, *, is_fallback: bool,
         latency_ms: int | None = None, model: str | None = None, parts: dict | None = None) -> AiInsightReport:
    assert kind in KINDS, kind
    parts = parts or fingerprint_parts(user_id)
    row = AiInsightReport(
        user_id=user_id, kind=kind, data=json.dumps(data, ensure_ascii=False, default=str),
        signals=json.dumps(signals, ensure_ascii=False, default=str),
        fingerprint=fingerprint(parts), fingerprint_parts=json.dumps(parts),
        as_of_date=date.fromisoformat(parts["date"]), is_fallback=is_fallback,
        latency_ms=latency_ms, model=model, generated_at=datetime.now(timezone.utc),
    )
    db.session.add(row)
    db.session.commit()
    return row


def latest(user_id: int, kind: str, before_id: int | None = None) -> AiInsightReport | None:
    q = AiInsightReport.query.filter_by(user_id=user_id, kind=kind)
    if before_id is not None:
        q = q.filter(AiInsightReport.id < before_id)
    return q.order_by(AiInsightReport.id.desc()).first()


def staleness(row: AiInsightReport, user_id: int) -> dict:
    """{"stale": bool, "changed": ["date"|"tasks"|"plan", …]} — compares stored and current data."""
    now = fingerprint_parts(user_id)
    old = json.loads(row.fingerprint_parts or "{}")
    changed = [k for k in ("date", "tasks", "plan") if old.get(k) != now.get(k)]
    return {"stale": bool(changed), "changed": changed}


def payload(user_id: int, kind: str) -> dict | None:
    """The latest stored result + whether the farm changed since. No AI call."""
    row = latest(user_id, kind)
    if row is None:
        return None
    st = staleness(row, user_id)
    return {
        "id": row.id, "kind": row.kind, "data": json.loads(row.data), "signals": json.loads(row.signals),
        "is_fallback": row.is_fallback, "generated_at": row.generated_at.isoformat() + ("Z" if row.generated_at.tzinfo is None else ""),
        "as_of_date": row.as_of_date.isoformat(), "latency_ms": row.latency_ms, "model": row.model,
        "stale": st["stale"], "changed": st["changed"], "banner": CHANGED_BANNER if st["stale"] else None,
    }


def what_changed(previous: list | None, current: list) -> dict:
    """Signals added / gone / changed since the previous report, matched by their stable key."""
    if previous is None:
        return {"first_report": True, "added": [], "removed": [], "changed": []}
    prev = {s["key"]: s for s in previous}
    cur = {s["key"]: s for s in current}
    return {
        "first_report": False,
        "added": [cur[k] for k in cur if k not in prev],
        "removed": [prev[k] for k in prev if k not in cur],
        "changed": [{"before": prev[k], "after": cur[k]} for k in cur if k in prev and prev[k]["text"] != cur[k]["text"]],
    }
