from app.repositories.field_repository import FieldRepository
from app.repositories.task_repository import TaskRepository


class FieldService:

    @staticmethod
    def create_field(data):
        return FieldRepository.create(data)

    @staticmethod
    def get_all_fields():
        return FieldRepository.get_all()

    @staticmethod
    def get_field_by_id(field_id):
        return FieldRepository.get_by_id(field_id)

    @staticmethod
    def delete_field(field_id):
        field = FieldRepository.get_by_id(field_id)
        if field:
            FieldRepository.delete(field)
        return field

    @staticmethod
    def update_field(field_id, data):
        field = FieldRepository.get_by_id(field_id)
        if field:
            FieldRepository.update(field, data)
        return field

    @staticmethod
    def get_currently_active_fields():
        return FieldRepository.get_all_active()

    @staticmethod
    def get_active_fields_with_tasks():
        fields = FieldRepository.get_all_active()
        tasks = TaskRepository.get_pending_field_tasks()
        return {"fields": fields, "tasks": tasks}

    @staticmethod
    def get_all_field_tasks():
        return TaskRepository.get_all_field_tasks()

    @staticmethod
    def get_pending_field_tasks():
        return TaskRepository.get_pending_field_tasks()

    @staticmethod
    def get_pending_tasks_by_field_id(field_id):
        return TaskRepository.get_pending_tasks_by_field_id(field_id)

    @staticmethod
    def get_field_summary(field_id):
        field = FieldRepository.get_by_id(field_id)
        if not field:
            return None
        return {
            "id": field.id,
            "name": field.name,
            "acreage": field.acreage,
            "growth_stage": field.growth_stage,
            "health_status": field.health_status,
            "field_score": field.field_score,
            "health_percentage": field.health_percentage,
            "moisture_level": field.moisture_level,
            "heat_level": field.heat_level,
            "stress_risk": field.stress_risk,
            "disease_risk": field.disease_risk,
            "currently_active": field.currently_active,
            "crop": {
                "id": field.crop.id if field.crop else None,
                "name": field.crop.name if field.crop else None,
            },
            "task_count": len(field.tasks),
            "pending_task_count": len([t for t in field.tasks if not t.completed]),
        }

    @staticmethod
    def get_field_status(field):
        if field.health_status == "good":
            return "Healthy"
        elif field.health_status == "warning":
            return "Needs attention"
        return "At risk"
