from app.extensions import db

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    priority = db.Column(db.String(20))  # high, medium, low
    due_date = db.Column(db.Date)
    crop_id = db.Column(db.Integer)
    completed = db.Column(db.Boolean, default=False)