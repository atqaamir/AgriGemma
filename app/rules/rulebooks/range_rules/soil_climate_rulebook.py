from app.extensions import db


class SoilClimateRulebook(db.Model):
    __tablename__ = "soil_climate_rulebook"

    id      = db.Column(db.Integer, primary_key=True)
    crop_id = db.Column(db.Integer, nullable=False)

    N_min  = db.Column(db.Float)
    N_max  = db.Column(db.Float)
    N_mean = db.Column(db.Float)

    P_min  = db.Column(db.Float)
    P_max  = db.Column(db.Float)
    P_mean = db.Column(db.Float)

    K_min  = db.Column(db.Float)
    K_max  = db.Column(db.Float)
    K_mean = db.Column(db.Float)

    ph_min  = db.Column(db.Float)
    ph_max  = db.Column(db.Float)
    ph_mean = db.Column(db.Float)

    organic_matter_min  = db.Column(db.Float)
    organic_matter_max  = db.Column(db.Float)
    organic_matter_mean = db.Column(db.Float)

    soil_moisture_min  = db.Column(db.Float)
    soil_moisture_max  = db.Column(db.Float)
    soil_moisture_mean = db.Column(db.Float)

    def get_range(rulebook, crop_id):
        pass

    def in_range(rulebook, *keys, column, value):
        pass
