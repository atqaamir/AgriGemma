"""Actual-dates layer on top of the seasonal plan.

The seasonal plan holds the *planned* dates and is never modified by daily
operations. A PlanEventOverride records what actually happens to a one-time
event of a seasonal plan entry:

- forecast_shift   : a forecast rule moved the event (e.g. sowing delayed by heat),
                     including dates cascaded from a sowing delay.
- farmer_completed : the farmer marked the task done (actual sowing date),
                     including dates cascaded from the actual sowing date.
- farmer_planned   : the farmer decided to "sow anyway" on a date (decision needed /
                     overdue), including cascaded dates. It wins over forecast_shift (the
                     daily re-plan never moves it) and loses to farmer_completed. Undo
                     deletes these rows.

Effective date of an event = latest applicable override, otherwise the seasonal date.
`as_of_date` is the day whose decision produced the override (daily update date or
task completion date); it makes reruns on the same day idempotent.
"""
from datetime import datetime

from app.extensions import db


class PlanEventOverride(db.Model):
    __tablename__ = "plan_event_override"

    EVENT_TYPES = ("sowing", "fertilization", "harvesting", "irrigation_start")
    SOURCE_FORECAST = "forecast_shift"
    SOURCE_FARMER = "farmer_completed"
    SOURCE_FARMER_PLANNED = "farmer_planned"

    id                     = db.Column(db.Integer, primary_key=True)
    seasonal_plan_entry_id = db.Column(db.Integer, db.ForeignKey("seasonal_plan_entry.id"), nullable=False, index=True)
    event_type             = db.Column(db.String(30), nullable=False)
    original_date          = db.Column(db.Date, nullable=True)    # effective date before this override
    actual_date            = db.Column(db.Date, nullable=False)
    source                 = db.Column(db.String(30), nullable=False)
    reason                 = db.Column(db.Text, nullable=True)    # human-readable rule / action text
    as_of_date             = db.Column(db.Date, nullable=False)   # day of the decision
    task_id                = db.Column(db.Integer, db.ForeignKey("task.id"), nullable=True)  # farmer_completed only
    created_at             = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("seasonal_plan_entry_id", "event_type", "source", "as_of_date",
                            name="uq_override_entry_event_source_day"),
    )

    def __repr__(self):
        return (f"<PlanEventOverride entry={self.seasonal_plan_entry_id} {self.event_type} "
                f"{self.original_date}→{self.actual_date} {self.source} as_of={self.as_of_date}>")
