"""Keeps details of the weekly plan for the user, including the crops to be planted, fields to be worked on, and tasks to be performed."""

from app.extensions import db

class WeeklyPlan(db.Model): 
    __tablename__ = "weekly_plan"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    plan_start_date = db.Column(db.Date, nullable=False)
    plan_end_date = db.Column(db.Date, nullable=False)
    
    class PlanDetail(db.Model):
        __tablename__ = "crop_plan"

        id = db.Column(db.Integer, primary_key=True)
        crop_id = db.Column(db.Integer, db.ForeignKey("crop.id"), nullable=False)
        field_id = db.Column(db.Integer, db.ForeignKey("field.id"), nullable=False)
        tasks = db.Column(db.Text, nullable=True)  # JSON string of tasks for the week:
        # [{"task_type": "field", "task": "Planting", "date_range": "2024-09-01 to 2024-09-07"}, {"task_type":"crop", "task": "Irrigation", "date_range": "2024-09-08 to 2024-09-14"}]
        weekly_plan_id = db.Column(db.Integer, db.ForeignKey("weekly_plan.id"), nullable=False)
