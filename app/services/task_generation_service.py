from app.services.domain_service.field_service import FieldService
from app.services.domain_service.crop_service import CropService
class TaskGenerationService:
    def __init__(self):
        pass

    def generate_daily_tasks(self, field_id, weekly_plan):
        # Placeholder logic for task generation based on field conditions
        field = FieldService().get_field_by_id(field_id)
        tasks = []
        if field.moisture_level is not None and field.moisture_level < 30:
            tasks.append("Irrigation needed")
        if field.health_status == "Poor":
            tasks.append("Pest control needed")
        return tasks
