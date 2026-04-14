from datetime import datetime
from app.extensions import db


class ClimateProfile(db.Model):
    __tablename__ = "climate_profiles"

    id = db.Column(db.Integer, primary_key=True)

    region = db.Column(db.String(100), nullable=False)
    season = db.Column(db.String(50), nullable=True)   # e.g. Kharif, Rabi, Summer
    month = db.Column(db.String(20), nullable=True)    # e.g. January, July
    crop_type = db.Column(db.String(100), nullable=True)

    avg_temperature_c = db.Column(db.Float, nullable=True)
    avg_rainfall_mm = db.Column(db.Float, nullable=True)
    avg_humidity = db.Column(db.Float, nullable=True)

    drought_risk = db.Column(db.String(20), nullable=True)      # low, medium, high
    flood_risk = db.Column(db.String(20), nullable=True)
    heatwave_risk = db.Column(db.String(20), nullable=True)

    planting_window_start = db.Column(db.String(20), nullable=True)
    planting_window_end = db.Column(db.String(20), nullable=True)

    notes = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "region": self.region,
            "season": self.season,
            "month": self.month,
            "crop_type": self.crop_type,
            "avg_temperature_c": self.avg_temperature_c,
            "avg_rainfall_mm": self.avg_rainfall_mm,
            "avg_humidity": self.avg_humidity,
            "drought_risk": self.drought_risk,
            "flood_risk": self.flood_risk,
            "heatwave_risk": self.heatwave_risk,
            "planting_window_start": self.planting_window_start,
            "planting_window_end": self.planting_window_end,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

