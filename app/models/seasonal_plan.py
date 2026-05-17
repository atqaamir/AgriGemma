"""Seasonal planning models.

SeasonalPlan      - top-level plan for a user (shared: growth stage, active flag).
SeasonalPlanEntry - one entry per crop within a plan (all per-crop schedule fields).
"""
from datetime import datetime, timezone

from app.extensions import db


class SeasonalPlan(db.Model):
    __tablename__ = "seasonal_plan"

    id               = db.Column(db.Integer, primary_key=True)
    user_id          = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    growth_stage_id  = db.Column(db.Integer, nullable=True)
    currently_active = db.Column(db.Boolean, default=True, nullable=False)
    last_updated     = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=True)
    ai_explanation   = db.Column(db.Text,    nullable=True)   # JSON: { "CropName": "explanation" } for Not Feasible crops only

    entries = db.relationship(
        "SeasonalPlanEntry",
        back_populates="plan",
        cascade="all, delete-orphan",
    )


class SeasonalPlanEntry(db.Model):
    __tablename__ = "seasonal_plan_entry"

    id              = db.Column(db.Integer, primary_key=True)
    plan_id         = db.Column(db.Integer, db.ForeignKey("seasonal_plan.id"), nullable=False)

    crop_name_id    = db.Column(db.Integer, db.ForeignKey("crop_names.id"), nullable=False)
    soil_id         = db.Column(db.Integer, db.ForeignKey("soil_type.id"), nullable=True)
    water_source_id = db.Column(db.Integer, db.ForeignKey("water_source.id"), nullable=True)
    growth_id       = db.Column(db.Integer, db.ForeignKey("growth_stage.id"), nullable=True)

    sowing                = db.Column(db.String(20), nullable=True)   # "MM/DD/YYYY"
    harvesting            = db.Column(db.String(20), nullable=True)   # "MM/DD/YYYY"
    irrigation_start_date = db.Column(db.String(20), nullable=True)   # "MM/DD/YYYY"
    irrigation_frequency  = db.Column(db.Integer,    nullable=True)   # times / week
    fertilization_date    = db.Column(db.String(20), nullable=True)   # "MM/DD/YYYY"
    adjustments_to_make   = db.Column(db.Text,       nullable=True)   # JSON-serialised list
    feasibility           = db.Column(db.String(20), nullable=True)   # "Ideal", "Conditional", "Not Feasible"

    plan          = db.relationship("SeasonalPlan", back_populates="entries")
    crop_name_rel = db.relationship("CropNames",    lazy="joined", foreign_keys=[crop_name_id])
    soil_rel      = db.relationship("Soil_Type",    lazy="joined", foreign_keys=[soil_id])
    water_rel     = db.relationship("WaterSource",  lazy="joined", foreign_keys=[water_source_id])
    growth_rel    = db.relationship("GrowthStage",  lazy="joined", foreign_keys=[growth_id])
