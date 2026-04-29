def get_mock_soil_data(field_name: str) -> dict:
    return {
        "field_name": field_name,
        "moisture_percent": 22,
        "temperature_c": 29,
        "ph": 6.8,
        "condition": "Dry",
    }


def get_mock_crop_data(crop_name: str, field_name: str) -> dict:
    return {
        "name": crop_name,
        "field_name": field_name,
        "field_size_acres": 4.5,
        "planting_date": "2026-03-01",
        "growth_stage": "Flowering",
        "health_status": "Warning",
        "days_since_planting": 44,
    }