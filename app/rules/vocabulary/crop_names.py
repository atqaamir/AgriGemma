from app.extensions import db

class CropNames(db.Model):
    __tablename__ = "crop_names"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

