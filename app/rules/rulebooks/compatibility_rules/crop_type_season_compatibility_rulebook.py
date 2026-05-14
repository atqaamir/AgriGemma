from app.extensions import db


class CropTypeSeasonCompatibilityRulebook(db.Model):
    __tablename__ = "crop_type_season_compatibility_rulebook"

    id           = db.Column(db.Integer, primary_key=True)
    crop_type_id = db.Column(db.Integer, nullable=False)
    season_id    = db.Column(db.Integer, nullable=False)
    score        = db.Column(db.Float,     nullable=False)
    feasibility  = db.Column(db.String(20), nullable=False)

    def get_score(rulebook, crop_type_id, season_id):
        pass
