"""Keeps details of the user's seasonal planting plans, including crop selection, sowing and harvesting dates, irrigation schedules, and expected yields."""
from app.extensions import db

class SeasonalPlan(db.Model):
    __tablename__ = "seasonal_plan"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)  

    crop_id = db.Column(db.Integer, db.ForeignKey("crop.id"), nullable=False)
    crop_sow_date = db.Column(db.Date, nullable=True)
    crop_harvest_date = db.Column(db.Date, nullable=True)
    crop_irrigation_dates = db.Column(db.String(255), nullable=True)  # e.g., "2024-05-01,2024-05-15,2024-06-01"
    expected_yield = db.Column(db.Float, nullable=True)
    currently_active = db.Column(db.Boolean, default=True, nullable=False)  
    crop_irrigation_schedule = db.Column(db.String(255), nullable=True)  # e.g., "Every 3 days" or "Twice a week"
    crop_irrigation_amount = db.Column(db.Float, nullable=True)   # Amount of water in liters per irrigation session

