"""Weekly planning models.

WeeklyPlan       - top-level record for a user's weekly plan.
WeeklyPlanEntry  - one row per crop-field pair within the plan.
"""

from datetime import datetime
from app.extensions import db


class WeeklyPlan(db.Model):
    __tablename__ = "weekly_plan"

    id               = db.Column(db.Integer, primary_key=True)
    user_id          = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    week_start_date  = db.Column(db.Date, nullable=False)
    week_end_date    = db.Column(db.Date, nullable=False)
    generated_at     = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    currently_active = db.Column(db.Boolean, default=True, nullable=False)

    # Which seasonal plan this was based on (null if fallback to Crop model)
    seasonal_plan_id = db.Column(db.Integer, nullable=True)

    entries = db.relationship(
        "WeeklyPlanEntry",
        back_populates="plan",
        cascade="all, delete-orphan",
    )


class WeeklyPlanEntry(db.Model):
    __tablename__ = "weekly_plan_entry"

    id             = db.Column(db.Integer, primary_key=True)
    weekly_plan_id = db.Column(db.Integer, db.ForeignKey("weekly_plan.id"), nullable=False)

    crop_id         = db.Column(db.Integer, nullable=False)   # CropNames.id
    field_id        = db.Column(db.Integer, nullable=True)    # Field.id
    growth_stage_id = db.Column(db.Integer, nullable=True)

    # JSON-serialised pre-adjustment events (raw schedule, no climate changes):
    # [{ "event_type", "date" }]
    original_events = db.Column(db.Text, nullable=True)

    # JSON-serialised post-adjustment events (dates shifted by climate rules):
    # [{ "event_type", "date" }]
    week_events = db.Column(db.Text, nullable=True)

    # JSON-serialised plan-level climate adjustments:
    # [{ "factor", "reasoning", "adjustment" }]
    climate_adjustments = db.Column(db.Text, nullable=True)

    plan = db.relationship("WeeklyPlan", back_populates="entries")
