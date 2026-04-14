from datetime import datetime
from app.extensions import db


class Pesticide(db.Model):
    __tablename__ = "pesticides"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(120), nullable=False)
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

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "brand": self.brand,
            "active_ingredient": self.active_ingredient,
            "target_pest": self.target_pest,
            "crop_type": self.crop_type,
            "recommended_dosage": self.recommended_dosage,
            "application_method": self.application_method,
            "waiting_period_days": self.waiting_period_days,
            "safety_notes": self.safety_notes,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }