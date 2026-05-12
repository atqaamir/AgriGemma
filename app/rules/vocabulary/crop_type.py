from app.extensions import db


class CropType(db.Model):
    __tablename__ = "crop_type"

    id   = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
