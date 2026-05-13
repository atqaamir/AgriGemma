from app.extensions import db


class SeasonNames(db.Model):
    __tablename__ = "season_names"

    id   = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
