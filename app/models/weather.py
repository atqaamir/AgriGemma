"""Daily weather records used for weekly plan climate lookups.

ClimateProfile  - one row per (region, date); seeded manually, later replaced by API feed.
"""

from datetime import datetime
from app.extensions import db


class Weather(db.Model):
    __tablename__ = "weather"

    id                = db.Column(db.Integer, primary_key=True)
    region            = db.Column(db.String(100), nullable=False)   # matches Field.location
    date              = db.Column(db.Date,        nullable=False)   # lookup key

    avg_temperature_c = db.Column(db.Float, nullable=True)   # °C
    humidity          = db.Column(db.Float, nullable=True)   # %
    rainfall_mm       = db.Column(db.Float, nullable=True)   # mm / day
    sunlight_hours    = db.Column(db.Float, nullable=True)   # hours of sun / day
    wind_speed_kph    = db.Column(db.Float, nullable=True)   # km/h (stored; not yet in rules)

    notes        = db.Column(db.Text,       nullable=True)
    changes      = db.Column(db.Text,       nullable=True)   # JSON: [{"change_type": "temperature", "new_value": 35.5}]
    change_level = db.Column(db.String(10), nullable=True)   # "high" | "low"
    created_at   = db.Column(db.DateTime,   default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id":                self.id,
            "region":            self.region,
            "date":              self.date.isoformat() if self.date else None,
            "avg_temperature_c": self.avg_temperature_c,
            "humidity":          self.humidity,
            "rainfall_mm":       self.rainfall_mm,
            "sunlight_hours":    self.sunlight_hours,
            "wind_speed_kph":    self.wind_speed_kph,
            "notes":             self.notes,
            "changes":           self.changes,
            "change_level":      self.change_level,
            "created_at":        self.created_at.isoformat() if self.created_at else None,
        }

class WeatherProfile(db.Model):
    __tablename__ = "weather_profiles"

    id = db.Column(db.Integer, primary_key=True)
    date              = db.Column(db.Date,        nullable=False)   # lookup key

    region = db.Column(db.String(100), nullable=False)
    avg_temperature_c = db.Column(db.Float, nullable=True)   # °C
    humidity          = db.Column(db.Float, nullable=True)   # %
    rainfall_mm       = db.Column(db.Float, nullable=True)   # mm / day
    sunlight_hours    = db.Column(db.Float, nullable=True)   # hours of sun / day
    wind_speed_kph    = db.Column(db.Float, nullable=True)   # km/h (stored; not yet in rules)
    
    notes      = db.Column(db.Text,     nullable=True)
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

