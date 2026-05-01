""" Keeps historical records of all crops cultivated, their growth stages, health status, and other relevant information for analysis and reporting purposes.
"""
from app.extensions import db

class CropHistory(db.Model):
    __tablename__ = "crophistory"

    id = db.Column(db.Integer, primary_key=True)
    crop_id = db.Column(db.Integer, db.ForeignKey('crop.id'), nullable=False)
    field_id = db.Column(db.Integer, db.ForeignKey('field.id'), nullable=False)
    growth_stage = db.Column(db.String(50), nullable=True)
    growth_stage_start_date = db.Column(db.Date, nullable=True)
    growth_stage_end_date = db.Column(db.Date, nullable=True)
    current_health_status = db.Column(db.String(50), nullable=True)
    water_requirement = db.Column(db.Float, nullable=True)
    heath_requirement = db.Column(db.Float, nullable=True)
    soil_health_status = db.Column(db.String(50), nullable=True)
    growth_stage_status = db.Column(db.Boolean, default=True, nullable=False)
