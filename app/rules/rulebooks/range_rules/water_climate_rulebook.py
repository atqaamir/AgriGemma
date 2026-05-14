from app.extensions import db


class WaterClimateRulebook(db.Model):
    __tablename__ = "water_climate_rulebook"

    id              = db.Column(db.Integer, primary_key=True)
    crop_id         = db.Column(db.Integer, nullable=False)
    growth_stage_id = db.Column(db.Integer, nullable=False)
    soil_type_id    = db.Column(db.Integer, nullable=False)

    soil_moisture_min  = db.Column(db.Float)
    soil_moisture_max  = db.Column(db.Float)
    soil_moisture_mean = db.Column(db.Float)

    rainfall_min  = db.Column(db.Float)
    rainfall_max  = db.Column(db.Float)
    rainfall_mean = db.Column(db.Float)

    def get_range(rulebook, crop_id, growth_stage_id, soil_type_id):
        pass

    def in_range(rulebook, *keys, column, value):
        pass
