"""Keeps tracks of the tasks geenrated for the user, along with their details and associated crop and field information."""
from datetime import datetime
from app.extensions import db


class Task(db.Model):
    __tablename__ = "task"

    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(200), nullable=False)
    priority = db.Column(db.String(20), nullable=False)  # critical, high, medium, low
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    due_date = db.Column(db.Date, nullable=True)
    completed = db.Column(db.Boolean, default=False, nullable=False)

    task_type = db.Column(db.String(50), nullable=True) # planting, irrigation, fertilization, harvesting, maintenance, checkup    
    task_category = db.Column(db.String(50), nullable=True)  # crop, field, general
    description = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)

    crop_id = db.Column(db.Integer, db.ForeignKey("crop.id"), nullable=True)
    field_id = db.Column(db.Integer, db.ForeignKey("field.id"), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)

    crop = db.relationship(
        "Crop",
        back_populates="tasks",
        foreign_keys=[crop_id],
        lazy="select",
    )

    field = db.relationship(
        "Field",
        back_populates="tasks",
        foreign_keys=[field_id],
        lazy="select",
    )



    def __repr__(self):
        return f"<Task {self.id} - {self.title}>"