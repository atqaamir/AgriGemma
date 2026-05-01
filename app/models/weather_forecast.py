"""Keep weekly snapshot data records of the weather forecasts fechted from the API for change detection 
This can help in understanding trends and making informed decisions for weekly plan changes.
Fetched daily."""


from datetime import datetime
from app.extensions import db


class CurrentWeatherProfile(db.Model):
    __tablename__ = "current_weather_profiles"

    id = db.Column(db.Integer, primary_key=True)

    region = db.Column(db.String(100), nullable=False)
    season = db.Column(db.String(50), nullable=True)   # e.g. Kharif, Rabi, Summer

    avg_temperature_c = db.Column(db.Float, nullable=True)
    avg_rainfall_mm = db.Column(db.Float, nullable=True)
    avg_humidity = db.Column(db.Float, nullable=True)
    
    notes = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    _start_index = db.Column(db.Integer, nullable=False)  # To track the start of a consecutive date sequence
    _with_increments = db.Column(db.Integer, default=7, nullable=False)  # To track how many consecutive dates are together
  
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

