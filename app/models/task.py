from app.extensions import db

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    priority = db.Column(db.String(20))  # high, medium, low
    created_at = db.Column(db.Date, default=db.func.current_timestamp())
    due_date = db.Column(db.Date)
    completed = db.Column(db.Boolean, default=False)
    task_type = db.Column(db.String(50))  # e.g., irrigation, fertilization, harvesting, pest control
    task_category = db.Column(db.String(50))  # e.g., crop, field, general
    description = db.Column(db.Text)
    assigned_to = db.Column(db.String(100))  # e.g., worker name or team
    notes = db.Column(db.Text)
    crop_id = db.Column(db.Integer, db.foreignKey('crop.id'), nullable=True)
    field_id = db.Column(db.Integer, db.foreignKey('field.id'), nullable=True)
    pesticide_id = db.Column(db.Integer, db.foreignKey('pesticides.id'), nullable=True)
    
    