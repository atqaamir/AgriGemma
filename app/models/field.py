from app.extensions import db

class Field(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    size = db.Column(db.Float)  # acres
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))