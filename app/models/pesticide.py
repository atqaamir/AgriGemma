from app.extensions import db
from datetime import datetime


class Pesticide(db.Model):
    __tablename__ = "pesticide"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

    brand = db.Column(db.String(120), nullable=True)
    active_ingredient = db.Column(db.String(120), nullable=True)

    target_pest = db.Column(db.String(120), nullable=True)
    crop_type = db.Column(db.String(100), nullable=True)

    recommended_dosage = db.Column(db.String(100), nullable=True)
    application_method = db.Column(db.String(120), nullable=True)

    waiting_period_days = db.Column(db.Integer, nullable=True)
    safety_notes = db.Column(db.Text, nullable=True)

    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

