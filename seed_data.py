from datetime import date, datetime

from app.extensions import db
from app.models.notification import Notification
from app.models.user import User
from app.models.crop import Crop
from app.models.field import Field
from app.models.task import Task


def run():
    # Clear existing data (respect FK order)
    Task.query.delete()
    Notification.query.delete()
    Crop.query.delete()
    Field.query.delete()
    User.query.delete()
    db.session.commit()

    # User
    user = User(name="Demo Farmer", location="Punjab, Pakistan")
    db.session.add(user)
    db.session.commit()

    # Fields
    sample_fields = [
        Field(name="North Field Alpha", user_id=user.id, acreage=12.5, health_status="healthy",
              field_score=92.0, moisture_level=65.0, heat_level=28.0,
              stress_risk=10.0, currently_active=True, health_percentage=92.0),

        Field(name="East Creek Basin", user_id=user.id, acreage=34.2, health_status="alert",
              field_score=64.0, moisture_level=45.0, heat_level=25.0,
              stress_risk=35.0, currently_active=True, health_percentage=64.0),

        Field(name="South Hill Slope", user_id=user.id, acreage=18.0, health_status="critical",
              field_score=88.0, moisture_level=60.0, heat_level=27.0,
              stress_risk=15.0, currently_active=False, health_percentage=88.0),

        Field(name="The Reservoir", user_id=user.id, acreage=5.5, health_status="healthy",
              field_score=95.0, moisture_level=70.0, heat_level=30.0,
              stress_risk=8.0, currently_active=False, health_percentage=95.0),
    ]

    db.session.add_all(sample_fields)
    db.session.commit()

    # Crops
    crop_data = [
        {"crop_name_id": 1, "user_id": user.id, "planting_date": date.today(),
         "current_growth_stage_id": 1, "current_health_status": "healthy",
         "currently_water_requirement": 25.5, "currently_active": True,
         "field_id": sample_fields[0].id},

        {"crop_name_id": 2, "user_id": user.id, "planting_date": date.today(),
         "current_growth_stage_id": 3, "current_health_status": "alert",
         "currently_water_requirement": 18.0, "currently_active": True,
         "field_id": sample_fields[1].id},

        {"crop_name_id": 3, "user_id": user.id, "planting_date": date.today(),
         "current_growth_stage_id": 2, "current_health_status": "critical",
         "currently_water_requirement": 22.0, "currently_active": True,
         "field_id": sample_fields[2].id},

        {"crop_name_id": 1, "user_id": user.id, "planting_date": date.today(),
         "current_growth_stage_id": 2, "current_health_status": "healthy",
         "currently_water_requirement": 20.5, "currently_active": False,
         "field_id": sample_fields[3].id},
    ]

    crops = []
    for item in crop_data:
        crop = Crop(**item)
        db.session.add(crop)
        crops.append(crop)

    db.session.commit()

    north_field = sample_fields[0]
    maize_crop = crops[0]   # crop_name_id=1 (Maize), field=North Field Alpha

    # Tasks
    sample_tasks = [
        Task(title="Check equipment", priority="medium", created_at=datetime.utcnow(),
             due_date=date.today(), completed=False, task_type="maintenance",
             task_category="general", description="Inspect equipment.",
             notes="Focus on irrigation pump.", user_id=user.id),

        Task(title="Fertilize Maize", priority="high", created_at=datetime.utcnow(),
             due_date=date.today(), completed=False, task_type="fertilizing",
             task_category="crop", description="Apply nitrogen fertilizer.",
             crop_id=maize_crop.id, user_id=user.id),

        Task(title="Irrigate North Field Alpha", priority="high", created_at=datetime.utcnow(),
             due_date=date.today(), completed=False, task_type="irrigation",
             task_category="field", description="Run irrigation cycle.",
             field_id=north_field.id, user_id=user.id),
    ]

    db.session.add_all(sample_tasks)
    db.session.commit()

    # Notifications
    sample_notifications = [
        Notification(user_id=user.id, title="Crop Fertilization Required",
                     message="Maize requires fertilization today.",
                     notification_type="recommendation", is_read=False,
                     created_at=datetime.utcnow(), entity_type="crop",
                     entity_id=maize_crop.id),

        Notification(user_id=user.id, title="Field Moisture Warning",
                     message="Moisture level dropping.",
                     notification_type="warning", is_read=False,
                     created_at=datetime.utcnow(), entity_type="field",
                     entity_id=north_field.id),
    ]

    db.session.add_all(sample_notifications)
    db.session.commit()

    print("Seed complete")