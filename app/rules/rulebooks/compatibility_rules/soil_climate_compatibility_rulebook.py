from app.extensions import db


class SoilClimateCompatibilityRulebook(db.Model):
    __tablename__ = "soil_climate_compatibility_rulebook"

    id              = db.Column(db.Integer, primary_key=True)
    crop_id         = db.Column(db.Integer, nullable=False)
    growth_stage_id = db.Column(db.Integer, nullable=False)

    moisture_below_30             = db.Column(db.Float)
    moisture_below_30_feasibility = db.Column(db.String(20))
    moisture_30_60                = db.Column(db.Float)
    moisture_30_60_feasibility    = db.Column(db.String(20))
    moisture_above_60             = db.Column(db.Float)
    moisture_above_60_feasibility = db.Column(db.String(20))

    ph_below_6_5             = db.Column(db.Float)
    ph_below_6_5_feasibility = db.Column(db.String(20))
    ph_6_5_7_5               = db.Column(db.Float)
    ph_6_5_7_5_feasibility   = db.Column(db.String(20))
    ph_above_7_5             = db.Column(db.Float)
    ph_above_7_5_feasibility = db.Column(db.String(20))

    def get_score(rulebook, crop_id, factor, range_label):
        pass

    def in_range(rulebook, *keys, column, value):
        pass
