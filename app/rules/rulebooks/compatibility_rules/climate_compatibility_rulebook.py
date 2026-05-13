from app.extensions import db


class ClimateCompatibilityRulebook(db.Model):
    __tablename__ = "climate_compatibility_rulebook"

    id = db.Column(db.Integer, primary_key=True)
    crop_id = db.Column(db.Integer, nullable=False)

    temp_15_20 = db.Column(db.Float)
    temp_20_30 = db.Column(db.Float)
    temp_30_40 = db.Column(db.Float)

    humidity_below_40 = db.Column(db.Float)
    humidity_40_70    = db.Column(db.Float)
    humidity_above_70 = db.Column(db.Float)

    sunlight_below_4 = db.Column(db.Float)
    sunlight_4_8     = db.Column(db.Float)
    sunlight_above_8 = db.Column(db.Float)

    def get_score(rulebook, crop_id, factor, range_label):
        pass

    def in_range(rulebook, *keys, column, value):
        pass
