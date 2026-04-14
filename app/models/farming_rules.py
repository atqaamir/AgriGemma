from app.extensions import db
from datetime import datetime

class FarmingRule(db.Model):
    __tablename__ = "farming_rules"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)

    region = db.Column(db.String(100), nullable=True)
    crop_type = db.Column(db.String(100), nullable=True)
    growth_stage = db.Column(db.String(100), nullable=True)
    season = db.Column(db.String(50), nullable=True)

    min_temperature_c = db.Column(db.Float, nullable=True)
    max_temperature_c = db.Column(db.Float, nullable=True)

    min_soil_moisture = db.Column(db.Float, nullable=True)
    max_soil_moisture = db.Column(db.Float, nullable=True)

    rain_expected = db.Column(db.Boolean, nullable=True)
    heatwave_risk = db.Column(db.Boolean, nullable=True)

    action_type = db.Column(
        db.String(50),
        nullable=False
    )  # task, alert, recommendation, plan_adjustment

    action_message = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(20), default="medium")

    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def matches_runtime(self, weather: dict, soil: dict, crop: dict, farm: dict | None = None) -> bool:
        crop_name = (crop.get("name") or "").lower()
        crop_stage = (crop.get("growth_stage") or "").lower()
        temperature = weather.get("current", {}).get("temperature_c")
        soil_moisture = soil.get("moisture_percent")
        weather_rain_expected = weather.get("rain_expected")
        weather_heatwave_risk = weather.get("heatwave_risk")
        farm_region = ((farm or {}).get("region") or "").lower()

        if self.region and self.region.lower() != farm_region:
            return False

        if self.crop_type and self.crop_type.lower() != crop_name:
            return False

        if self.growth_stage and self.growth_stage.lower() != crop_stage:
            return False

        if self.min_temperature_c is not None and temperature is not None:
            if temperature < self.min_temperature_c:
                return False

        if self.max_temperature_c is not None and temperature is not None:
            if temperature > self.max_temperature_c:
                return False

        if self.min_soil_moisture is not None and soil_moisture is not None:
            if soil_moisture < self.min_soil_moisture:
                return False

        if self.max_soil_moisture is not None and soil_moisture is not None:
            if soil_moisture > self.max_soil_moisture:
                return False

        if self.rain_expected is not None and weather_rain_expected != self.rain_expected:
            return False

        if self.heatwave_risk is not None and weather_heatwave_risk != self.heatwave_risk:
            return False

        return self.is_active

    def matches_planning(self, climate_profile: dict, crop: dict, farm: dict | None = None) -> bool:
        crop_name = (crop.get("name") or "").lower()
        farm_region = ((farm or {}).get("region") or "").lower()

        climate_region = (climate_profile.get("region") or "").lower()
        climate_season = (climate_profile.get("season") or "").lower()
        avg_temp = climate_profile.get("avg_temperature_c")

        if self.region and self.region.lower() not in [farm_region, climate_region]:
            return False

        if self.crop_type and self.crop_type.lower() != crop_name:
            return False

        if self.season and self.season.lower() != climate_season:
            return False

        if self.min_temperature_c is not None and avg_temp is not None:
            if avg_temp < self.min_temperature_c:
                return False

        if self.max_temperature_c is not None and avg_temp is not None:
            if avg_temp > self.max_temperature_c:
                return False

        return self.is_active

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "region": self.region,
            "crop_type": self.crop_type,
            "growth_stage": self.growth_stage,
            "season": self.season,
            "min_temperature_c": self.min_temperature_c,
            "max_temperature_c": self.max_temperature_c,
            "min_soil_moisture": self.min_soil_moisture,
            "max_soil_moisture": self.max_soil_moisture,
            "rain_expected": self.rain_expected,
            "heatwave_risk": self.heatwave_risk,
            "action_type": self.action_type,
            "action_message": self.action_message,
            "priority": self.priority,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }