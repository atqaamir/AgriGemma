from app.extensions import db

class Crop(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    field_id = db.Column(db.Integer)
    planting_date = db.Column(db.Date)
    health_status = db.Column(db.String(20))