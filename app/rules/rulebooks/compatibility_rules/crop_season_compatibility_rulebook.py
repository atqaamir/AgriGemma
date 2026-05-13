from app.extensions import db


class CropSeasonCompatibilityRulebook(db.Model):
    __tablename__ = "crop_season_compatibility_rulebook"

    id        = db.Column(db.Integer, primary_key=True)
    crop_id   = db.Column(db.Integer, nullable=False)
    season_id = db.Column(db.Integer, nullable=False)
    score     = db.Column(db.Float, nullable=False)

    def get_score(rulebook, crop_id, season_id):
        pass

    def in_range(rulebook, *keys, column, value):
        pass
