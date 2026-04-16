"""
Add sample fields to the database for testing
Run this once: python seed_fields.py
"""

from app import create_app, db
from app.models.field import Field
from app.models.crop import Crop
from datetime import datetime, date

app = create_app()

with app.app_context():
    # Clear existing data
    Field.query.delete()
    Crop.query.delete()

    # Add sample crops first
    crop_names = ["Corn", "Wheat", "Soybeans", "Sunflower"]
    crops = {}

    for crop_name in crop_names:
        crop = Crop(
            name=crop_name,
            growth_stage="Vegetative",
            health_status="Healthy",
            soil_type="Loamy",
            water_requirement=25.5,
            planting_date=date.today()
        )
        db.session.add(crop)
        crops[crop_name] = crop

    db.session.commit()

    # Add sample fields
    sample_fields = [
        Field(
            name="North Field Alpha",
            crop_type=crops["Corn"].id,
            size=12.5,
            health_status="healthy",
            field_score=92,
            growth_stage="Vegetative",
            moisture_level=65.0,
            heat_level=28.0,
            stress_risk=10.0,
            disease_risk="Low"
        ),
        Field(
            name="East Creek Basin",
            crop_type=crops["Wheat"].id,
            size=34.2,
            health_status="alert",
            field_score=64,
            growth_stage="Alert",
            moisture_level=45.0,
            heat_level=25.0,
            stress_risk=35.0,
            disease_risk="Medium"
        ),
        Field(
            name="South Hill Slope",
            crop_type=crops["Soybeans"].id,
            size=18.0,
            health_status="healthy",
            field_score=88,
            growth_stage="Flowering",
            moisture_level=60.0,
            heat_level=27.0,
            stress_risk=15.0,
            disease_risk="Low"
        ),
        Field(
            name="The Reservoir",
            crop_type=crops["Sunflower"].id,
            size=5.5,
            health_status="healthy",
            field_score=95,
            growth_stage="Ripening",
            moisture_level=70.0,
            heat_level=30.0,
            stress_risk=8.0,
            disease_risk="Very Low"
        ),
    ]

    for field in sample_fields:
        db.session.add(field)

    db.session.commit()
    print("✅ Sample crops and fields added successfully!")
    print(f"Total crops: {Crop.query.count()}")
    print(f"Total fields: {Field.query.count()}")

