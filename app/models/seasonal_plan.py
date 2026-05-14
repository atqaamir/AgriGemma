"""Keeps details of the user's seasonal planting plans, including crop selection,
sowing/harvesting dates, irrigation schedule, fertilization date, and any rule-based adjustments."""
from app.extensions import db


class SeasonalPlan(db.Model):
    __tablename__ = "seasonal_plan"

    id                    = db.Column(db.Integer, primary_key=True)
    user_id               = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    crop_id               = db.Column(db.Integer, nullable=False)
    soil_type_id          = db.Column(db.Integer, nullable=True)
    water_source_id       = db.Column(db.Integer, nullable=True)
    growth_stage_id       = db.Column(db.Integer, nullable=True)

    sowing                = db.Column(db.String(20),  nullable=True)   # "MM/DD/YYYY"
    harvesting            = db.Column(db.String(20),  nullable=True)   # "MM/DD/YYYY"
    irrigation_start_date = db.Column(db.String(20),  nullable=True)   # "MM/DD/YYYY"
    irrigation_frequency  = db.Column(db.Integer,     nullable=True)   # times / week
    fertilization_date    = db.Column(db.String(20),  nullable=True)   # "MM/DD/YYYY"

    adjustments_to_make   = db.Column(db.Text, nullable=True)          # JSON-serialised list
    currently_active      = db.Column(db.Boolean, default=True, nullable=False)
