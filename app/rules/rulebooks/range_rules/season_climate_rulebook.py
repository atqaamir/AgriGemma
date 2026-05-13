from app.extensions import db


class SeasonClimateRulebook(db.Model):
    __tablename__ = "season_climate_rulebook"

    id        = db.Column(db.Integer, primary_key=True)
    season_id = db.Column(db.Integer, nullable=False)

    temperature_min  = db.Column(db.Float)
    temperature_max  = db.Column(db.Float)
    temperature_mean = db.Column(db.Float)

    humidity_min  = db.Column(db.Float)
    humidity_max  = db.Column(db.Float)
    humidity_mean = db.Column(db.Float)

    rainfall_min  = db.Column(db.Float)
    rainfall_max  = db.Column(db.Float)
    rainfall_mean = db.Column(db.Float)

    sunlight_exposure_min  = db.Column(db.Float)
    sunlight_exposure_max  = db.Column(db.Float)
    sunlight_exposure_mean = db.Column(db.Float)

    wind_speed_min  = db.Column(db.Float)
    wind_speed_max  = db.Column(db.Float)
    wind_speed_mean = db.Column(db.Float)

    co2_concentration_min  = db.Column(db.Float)
    co2_concentration_max  = db.Column(db.Float)
    co2_concentration_mean = db.Column(db.Float)

    def get_range(rulebook, season_id):
        pass

    def in_range(rulebook, *keys, column, value):
        pass
