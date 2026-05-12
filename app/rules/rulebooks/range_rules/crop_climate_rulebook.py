from app.extensions import db


class ClimateRulebook(db.Model):
    __tablename__ = "climate_rulebook"

    id              = db.Column(db.Integer, primary_key=True)
    crop_id         = db.Column(db.Integer, nullable=False)
    growth_stage_id = db.Column(db.Integer, nullable=False)
    soil_type_id    = db.Column(db.Integer, nullable=False)

    temperature_min  = db.Column(db.Float)
    temperature_max  = db.Column(db.Float)
    temperature_mean = db.Column(db.Float)

    humidity_min  = db.Column(db.Float)
    humidity_max  = db.Column(db.Float)
    humidity_mean = db.Column(db.Float)

    sunlight_exposure_min  = db.Column(db.Float)
    sunlight_exposure_max  = db.Column(db.Float)
    sunlight_exposure_mean = db.Column(db.Float)

    wind_speed_min  = db.Column(db.Float)
    wind_speed_max  = db.Column(db.Float)
    wind_speed_mean = db.Column(db.Float)

    co2_concentration_min  = db.Column(db.Float)
    co2_concentration_max  = db.Column(db.Float)
    co2_concentration_mean = db.Column(db.Float)

    crop_density_min  = db.Column(db.Float)
    crop_density_max  = db.Column(db.Float)
    crop_density_mean = db.Column(db.Float)

    frost_risk_min  = db.Column(db.Float)
    frost_risk_max  = db.Column(db.Float)
    frost_risk_mean = db.Column(db.Float)

    def get_range(rulebook, crop_id, growth_stage_id, soil_type_id):
        pass

    def in_range(rulebook, *keys, column, value):
        pass
