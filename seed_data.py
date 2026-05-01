from datetime import date, datetime

from app import create_app
from app.extensions import db
from app.models.notification import Notification
from app.models.user import User
from app.models.crop import Crop
from app.models.field import Field
from app.models.task import Task

app = create_app()

with app.app_context():
    db.create_all()

    # Clear existing data in dependency order
    Task.query.delete()
    Field.query.delete()
    Crop.query.delete()
    User.query.delete()
    db.session.commit()

    # Add sample user
    user = User(name="Demo Farmer", location="Punjab, Pakistan")
    db.session.add(user)
    db.session.commit()


    # Add sample fields
    sample_fields = [
        Field(
            name="North Field Alpha",
            user_id=user.id,
   
            acreage=12.5,
            health_status="healthy",
            field_score=92.0,
            moisture_level=65.0,
            heat_level=28.0,
            stress_risk=10.0,
            currently_active=True,
            health_percentage=92.0,
        ),
        Field(
            name="East Creek Basin",
            user_id=user.id,
         
            acreage=34.2,
            health_status="alert",
            field_score=64.0,
            moisture_level=45.0,
            heat_level=25.0,
            stress_risk=35.0,
            currently_active=True,
            health_percentage=64.0,
        ),
        Field(
            name="South Hill Slope",
            user_id=user.id,
         
            acreage=18.0,
            health_status="critical",
            field_score=88.0,
            moisture_level=60.0,
            heat_level=27.0,
            stress_risk=15.0,
            currently_active=False,
            health_percentage=88.0,
        ),
        Field(
            name="The Reservoir",
            user_id=user.id,
        
            acreage=5.5,
            health_status="healthy",
            field_score=95.0,
            moisture_level=70.0,
            heat_level=30.0,
            stress_risk=8.0,
            currently_active=False,
            health_percentage=95.0,
        ),
    ]

    db.session.add_all(sample_fields)
    db.session.commit()

    # Add sample crops
    crop_data = [
        {
            "name": "Corn",
            "user_id": user.id,
            "planting_date": date.today(),
            "current_growth_stage": "Vegetative",
            "current_health_status": "healthy",
            "currently_water_requirement": 25.5,
            "currently_active": True,
            "field_id": sample_fields[0].id,
        },
        {
            "name": "Wheat",
            "user_id": user.id,
            "planting_date": date.today(),
            "current_growth_stage": "Seedling",
            "current_health_status": "alert",
            "field_id": sample_fields[1].id,
            "currently_water_requirement": 18.0,
            "currently_active": True,
        },
        {
            "name": "Soybeans",
            "user_id": user.id,
            "planting_date": date.today(),
            "current_growth_stage": "Flowering",
            "current_health_status": "critical",
            "field_id": sample_fields[2].id,
            "currently_water_requirement": 22.0,
            "currently_active": True,
        },
        {
            "name": "Sunflower",
            "user_id": user.id,
            "planting_date": date.today(),
            "current_growth_stage": "Ripening",
            "current_health_status": "healthy",
            "field_id": sample_fields[3].id,
            "currently_water_requirement": 20.5,
            "currently_active": False,
        },
    ]

    crops = {}
    for item in crop_data:
        crop = Crop(**item)
        db.session.add(crop)
        crops[item["name"]] = crop

    db.session.commit()

  

    north_field = sample_fields[0]
    east_field = sample_fields[1]
    south_field = sample_fields[2]

    # Add sample tasks
    sample_tasks = [
        Task(
            title="Check equipment",
            priority="medium",
            created_at=datetime.utcnow(),
            due_date=date.today(),
            completed=False,
            task_type="maintenance",
            task_category="general",
            description="Inspect tractors, pipes, and hand tools before field work begins.",
            notes="Focus on irrigation pump first.",
            user_id=user.id,
        ),
        Task(
            title="Review weather forecast",
            priority="low",
            created_at=datetime.utcnow(),
            due_date=date.today(),
            completed=False,
            task_type="planning",
            task_category="general",
            description="Check rainfall probability and temperature for the next 3 days.",
            notes="Plan irrigation accordingly.",
            user_id=user.id,
        ),
        Task(
            title="Fertilize Corn",
            priority="high",
            created_at=datetime.utcnow(),
            due_date=date.today(),
            completed=False,
            task_type="fertilizing",
            task_category="crop",
            description="Apply nitrogen fertilizer to improve vegetative growth.",
            notes="Use recommended dosage only.",
            crop_id=crops["Corn"].id,
            user_id=user.id,
        ),
        Task(
            title="Inspect Wheat Growth",
            priority="medium",
            created_at=datetime.utcnow(),
            due_date=date.today(),
            completed=False,
            task_type="inspection",
            task_category="crop",
            description="Check wheat crop for uneven development and dry patches.",
            notes="Take photos for records.",
            crop_id=crops["Wheat"].id,
            user_id=user.id,
        ),
        Task(
            title="Monitor Soybean Flowering",
            priority="medium",
            created_at=datetime.utcnow(),
            due_date=date.today(),
            completed=False,
            task_type="monitoring",
            task_category="crop",
            description="Review flowering consistency and leaf health.",
            notes="Record any pest activity.",
            crop_id=crops["Soybeans"].id,
            user_id=user.id,
        ),
        Task(
            title="Irrigate North Field Alpha",
            priority="high",
            created_at=datetime.utcnow(),
            due_date=date.today(),
            completed=False,
            task_type="irrigation",
            task_category="field",
            description="Run irrigation cycle for North Field Alpha due to moisture drop.",
            notes="Target lower-moisture zone on west side.",
            field_id=north_field.id,
            user_id=user.id,
        ),
        Task(
            title="Soil pH Testing",
            priority="medium",
            created_at=datetime.utcnow(),
            due_date=date.today(),
            completed=False,
            task_type="inspection",
            task_category="field",
            description="Collect samples and test soil pH in East Creek Basin.",
            notes="Compare with previous month.",
            field_id=east_field.id,
            user_id=user.id,
        ),
        Task(
            title="Check drainage at South Hill Slope",
            priority="low",
            created_at=datetime.utcnow(),
            due_date=date.today(),
            completed=False,
            task_type="maintenance",
            task_category="field",
            description="Inspect runoff path and ensure drainage is clear.",
            notes="Watch for erosion near lower edge.",
            field_id=south_field.id,
            user_id=user.id,
        ),
        Task(
            title="Spray East Creek Basin for fungal prevention",
            priority="high",
            created_at=datetime.utcnow(),
            due_date=date.today(),
            completed=False,
            task_type="spraying",
            task_category="field",
            description="Preventive spray for fungal risk in wheat section.",
            notes="Wear protective equipment and spray in early morning.",
            crop_id=crops["Wheat"].id,
            field_id=east_field.id,
            user_id=user.id,
        ),
    ]

    db.session.add_all(sample_tasks)
    db.session.commit()

    # =========================================================
    # SAMPLE NOTIFICATIONS
    # =========================================================

    sample_notifications = [

        Notification(
            user_id=user.id,

            title="Crop Fertilization Required",

            message="Corn requires fertilization today.",

            detail="""
    Corn in North Field Alpha has entered an aggressive vegetative
    growth phase. Nitrogen levels may decline rapidly during this
    stage, which can reduce overall crop performance and leaf
    development.

    Recommended action:
    • Apply nitrogen fertilizer within 24 hours
    • Avoid overwatering after fertilization
    • Monitor leaf coloration over the next 3 days
            """,

            notification_type="recommendation",

            is_read=False,

            created_at=datetime.utcnow(),

            entity_type="crop",

            entity_id=crops["Corn"].id,
        ),

        Notification(
            user_id=user.id,

            title="Task Due Today",

            message="Inspect Wheat Growth is due today.",

            detail="""
    The wheat inspection task scheduled for East Creek Basin
    should be completed today to identify uneven growth,
    moisture stress, or disease development.

    Suggested checks:
    • Inspect dry patches
    • Capture progress photos
    • Verify irrigation coverage
            """,

            notification_type="info",

            is_read=False,

            created_at=datetime.utcnow(),

            entity_type="task",

            entity_id=sample_tasks[3].id,
        ),

        Notification(
            user_id=user.id,

            title="Field Moisture Warning",

            message="North Field Alpha moisture level is decreasing.",

            detail="""
    Soil moisture levels have dropped below the recommended
    threshold for optimal crop performance.

    Potential risks:
    • Reduced nutrient absorption
    • Plant stress during afternoon heat
    • Slower vegetative growth

    Recommended action:
    Initiate irrigation cycle within the next 12 hours.
            """,

            notification_type="warning",

            is_read=False,

            created_at=datetime.utcnow(),

            entity_type="field",

            entity_id=north_field.id,
        ),

        Notification(
            user_id=user.id,

            title="Critical Crop Health Alert",

            message="Soybeans health status is critical.",

            detail="""
    The soybean crop in South Hill Slope is showing signs of
    high stress and declining health metrics.

    Detected indicators:
    • Elevated stress risk
    • Irregular flowering pattern
    • Moisture instability

    Immediate recommendations:
    • Inspect for pests or fungal infection
    • Review irrigation schedule
    • Conduct leaf health assessment
            """,

            notification_type="critical",

            is_read=False,

            created_at=datetime.utcnow(),

            entity_type="crop",

            entity_id=crops["Soybeans"].id,
        ),

        Notification(
            user_id=user.id,

            title="Spraying Reminder",

            message="Preventive spraying task is scheduled for East Creek Basin.",

            detail="""
    Preventive fungal spraying is recommended early in the morning
    to minimize evaporation and maximize treatment coverage.

    Safety recommendations:
    • Wear protective equipment
    • Avoid spraying during high wind
    • Keep irrigation paused for several hours after treatment
            """,

            notification_type="recommendation",

            is_read=True,

            created_at=datetime.utcnow(),

            entity_type="task",

            entity_id=sample_tasks[8].id,
        ),

        Notification(
            user_id=user.id,

            title="Weather Heat Advisory",

            message="High temperatures are expected tomorrow afternoon.",

            detail="""
    Forecast models predict elevated temperatures above normal
    seasonal averages tomorrow.

    Potential impacts:
    • Increased evaporation rates
    • Higher crop water demand
    • Heat stress risk during midday

    Recommendations:
    • Irrigate early morning
    • Avoid fertilizer application during peak heat
    • Monitor sensitive crops closely
            """,

            notification_type="warning",

            is_read=False,

            created_at=datetime.utcnow(),

            entity_type="weather",

            entity_id=None,
        ),
    ]

    db.session.add_all(sample_notifications)
    db.session.commit()

    print("Sample data seeded successfully.")
    print(f"Users: {User.query.count()}")
    print(f"Crops: {Crop.query.count()}")
    print(f"Fields: {Field.query.count()}")
    print(f"Tasks: {Task.query.count()}")
