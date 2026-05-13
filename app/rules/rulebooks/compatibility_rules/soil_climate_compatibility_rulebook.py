from app.extensions import db


class SoilClimateCompatibilityRulebook(db.Model):
    __tablename__ = "soil_climate_compatibility_rulebook"

    id = db.Column(db.Integer, primary_key=True)
    crop_id = db.Column(db.Integer, nullable=False)

    moisture_below_30 = db.Column(db.Float)
    moisture_30_60    = db.Column(db.Float)
    moisture_above_60 = db.Column(db.Float)

    ph_acidic   = db.Column(db.Float)
    ph_neutral  = db.Column(db.Float)
    ph_alkaline = db.Column(db.Float)

    def get_score(rulebook, crop_id, factor, range_label):
        pass

    def in_range(rulebook, *keys, column, value):
        pass
