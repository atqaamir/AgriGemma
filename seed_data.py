from datetime import date

from app import create_app
from app.extensions import db
from app.models.crop import Crop
from app.models.field import Field

app = create_app()

with app.app_context():
    # Create tables
    db.create_all()

    # Clear existing data
    Field.query.delete()
    Crop.query.delete()
    db.session.commit()

    # Add sample crops
    crop_data = [
        {
            "name": "Corn",
            "planting_date": date.today(),
            "growth_stage": "Vegetative",
            "health_status": "Healthy",
            "soil_type": "Loamy",
            "water_requirement": 25.5,
        },
        {
            "name": "Wheat",
            "planting_date": date.today(),
            "growth_stage": "Alert",
            "health_status": "Irrigation",
            "soil_type": "Clay",
            "water_requirement": 18.0,
        },
        {
            "name": "Soybeans",
            "planting_date": date.today(),
            "growth_stage": "Flowering",
            "health_status": "Healthy",
            "soil_type": "Loamy",
            "water_requirement": 22.0,
        },
        {
            "name": "Sunflower",
            "planting_date": date.today(),
            "growth_stage": "Ripening",
            "health_status": "Healthy",
            "soil_type": "Sandy",
            "water_requirement": 20.5,
        },
    ]

    crops = {}

    for item in crop_data:
        crop = Crop(**item)
        db.session.add(crop)
        crops[item["name"]] = crop

    db.session.commit()

    # Add sample fields
    sample_fields = [
        Field(
            name="North Field Alpha",
            crop_id=crops["Corn"].id,
            acreage=12.5,
            health_status="healthy",
            field_score=92,
            growth_stage="Vegetative",
            moisture_level=65.0,
            heat_level=28.0,
            stress_risk=10.0,
            disease_risk="Low",
            currently_active=True,
        ),
        Field(
            name="East Creek Basin",
            crop_id=crops["Wheat"].id,
            acreage=34.2,
            health_status="alert",
            field_score=64,
            growth_stage="Alert",
            moisture_level=45.0,
            heat_level=25.0,
            stress_risk=35.0,
            disease_risk="Medium",
            currently_active=True,
        ),
        Field(
            name="South Hill Slope",
            crop_id=crops["Soybeans"].id,
            acreage=18.0,
            health_status="healthy",
            field_score=88,
            growth_stage="Flowering",
            moisture_level=60.0,
            heat_level=27.0,
            stress_risk=15.0,
            disease_risk="Low",
            currently_active=False,
        ),
        Field(
            name="The Reservoir",
            crop_id=crops["Sunflower"].id,
            acreage=5.5,
            health_status="healthy",
            field_score=95,
            growth_stage="Ripening",
            moisture_level=70.0,
            heat_level=30.0,
            stress_risk=8.0,
            disease_risk="Very Low",
            currently_active=False,
        ),
    ]

    db.session.add_all(sample_fields)
    db.session.commit()

    print("✅ Sample crops and fields added successfully!")
    print(f"Total crops: {Crop.query.count()}")
    print(f"Total fields: {Field.query.count()}")