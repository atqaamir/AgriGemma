from app.extensions import db


class ClimateCompatibilityRulebook(db.Model):
    __tablename__ = "climate_compatibility_rulebook"

    id = db.Column(db.Integer, primary_key=True)
    crop_id = db.Column(db.Integer, nullable=False)
    growth_stage_id = db.Column(db.Integer, nullable=False)

    temp_15_20             = db.Column(db.Float)
    temp_15_20_feasibility = db.Column(db.String(20))
    temp_20_30             = db.Column(db.Float)
    temp_20_30_feasibility = db.Column(db.String(20))
    temp_30_40             = db.Column(db.Float)
    temp_30_40_feasibility = db.Column(db.String(20))

    humidity_below_40             = db.Column(db.Float)
    humidity_below_40_feasibility = db.Column(db.String(20))
    humidity_40_70                = db.Column(db.Float)
    humidity_40_70_feasibility    = db.Column(db.String(20))
    humidity_above_70             = db.Column(db.Float)
    humidity_above_70_feasibility = db.Column(db.String(20))

    sunlight_below_4             = db.Column(db.Float)
    sunlight_below_4_feasibility = db.Column(db.String(20))
    sunlight_4_8                 = db.Column(db.Float)
    sunlight_4_8_feasibility     = db.Column(db.String(20))
    sunlight_above_8             = db.Column(db.Float)
    sunlight_above_8_feasibility = db.Column(db.String(20))

    rainfall_below_50              = db.Column(db.Float)
    rainfall_below_50_feasibility  = db.Column(db.String(20))
    rainfall_50_100                = db.Column(db.Float)
    rainfall_50_100_feasibility    = db.Column(db.String(20))
    rainfall_100_200               = db.Column(db.Float)
    rainfall_100_200_feasibility   = db.Column(db.String(20))
    rainfall_200_300               = db.Column(db.Float)
    rainfall_200_300_feasibility   = db.Column(db.String(20))
    rainfall_above_300             = db.Column(db.Float)
    rainfall_above_300_feasibility = db.Column(db.String(20))

    def get_score(rulebook, crop_id, factor, range_label):
        pass

    def in_range(rulebook, *keys, column, value):
        pass
