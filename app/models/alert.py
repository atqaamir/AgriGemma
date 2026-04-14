from app.extensions import db

class Alert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String(200))
    level = db.Column(db.String(20))  # high, medium, low
    crop_id = db.Column(db.Integer)