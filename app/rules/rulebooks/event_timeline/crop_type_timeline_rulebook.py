from app.extensions import db


class CropTypeTimelineRulebook(db.Model):
    __tablename__ = "crop_type_timeline_rulebook"

    id           = db.Column(db.Integer, primary_key=True)
    crop_type_id = db.Column(db.Integer, nullable=False)

    sow_start_month     = db.Column(db.Integer, nullable=False)
    sow_end_month       = db.Column(db.Integer, nullable=False)
    harvest_start_month = db.Column(db.Integer, nullable=False)
    harvest_end_month   = db.Column(db.Integer, nullable=False)

    def get_timeline(rulebook, crop_type_id):
        pass
