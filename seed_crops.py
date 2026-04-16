"""
Add sample crops to the database for testing
Run this once: python seed_crops.py
"""

from datetime import date

from app import create_app
from app.extensions import db
from app.models.crop import Crop

app = create_app()

with app.app_context():
    # Create all tables first (important!)
    db.create_all()

    # Clear existing crops
    Crop.query.delete()
    db.session.commit()

    # Add sample crops
    sample_crops = [
        Crop(
            name="Corn",
            planting_date=date.today(),
            growth_stage="Vegetative",
            health_status="Healthy",
            soil_type="Loamy",
            water_requirement=25.5,
            field_id=None
        ),
        Crop(
            name="Wheat",
            planting_date=date.today(),
            growth_stage="Alert",
            health_status="Irrigation",
            soil_type="Clay",
            water_requirement=18.0,
            field_id=None
        ),
        Crop(
            name="Soybeans",
            planting_date=date.today(),
            growth_stage="Flowering",
            health_status="Healthy",
            soil_type="Loamy",
            water_requirement=22.0,
            field_id=None
        ),
        Crop(
            name="Sunflower",
            planting_date=date.today(),
            growth_stage="Ripening",
            health_status="Healthy",
            soil_type="Sandy",
            water_requirement=20.5,
            field_id=None
        ),
    ]

    db.session.add_all(sample_crops)
    db.session.commit()

    print("✅ Sample crops added successfully!")
    print(f"Total crops: {Crop.query.count()}")
