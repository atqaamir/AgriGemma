"""Seasonal planning models.

SeasonalPlan      - top-level plan for a user (shared: growth stage, active flag).
SeasonalPlanEntry - one entry per crop within a plan (all per-crop schedule fields).
"""
from app.extensions import db


class SeasonalPlan(db.Model):
    __tablename__ = "seasonal_plan"

    id               = db.Column(db.Integer, primary_key=True)
    user_id          = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    growth_stage_id  = db.Column(db.Integer, nullable=True)
    currently_active = db.Column(db.Boolean, default=True, nullable=False)

    entries = db.relationship(
        "SeasonalPlanEntry",
        back_populates="plan",
        cascade="all, delete-orphan",
    )


class SeasonalPlanEntry(db.Model):
    __tablename__ = "seasonal_plan_entry"

    id              = db.Column(db.Integer, primary_key=True)
    plan_id         = db.Column(db.Integer, db.ForeignKey("seasonal_plan.id"), nullable=False)

    crop_id         = db.Column(db.Integer, nullable=False)
    field_id        = db.Column(db.Integer, db.ForeignKey("field.id"), nullable=True)
    soil_type_id    = db.Column(db.Integer, nullable=True)
    water_source_id = db.Column(db.Integer, nullable=True)

    sowing                = db.Column(db.String(20), nullable=True)   # "MM/DD/YYYY"
    harvesting            = db.Column(db.String(20), nullable=True)   # "MM/DD/YYYY"
    irrigation_start_date = db.Column(db.String(20), nullable=True)   # "MM/DD/YYYY"
    irrigation_frequency  = db.Column(db.Integer,    nullable=True)   # times / week
    fertilization_date    = db.Column(db.String(20), nullable=True)   # "MM/DD/YYYY"
    adjustments_to_make   = db.Column(db.Text,       nullable=True)   # JSON-serialised list

    plan = db.relationship("SeasonalPlan", back_populates="entries")
