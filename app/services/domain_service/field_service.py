from app.repositories.field_repository import FieldRepository
from app.repositories.task_repository import TaskRepository
from app.rules.vocabulary.soil_type import Soil_Type
from app.rules.vocabulary.water_source import WaterSource


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
        """Active fields with their PENDING field-category tasks only."""
        fields = FieldRepository.get_all_active()
        all_tasks = []
        for field in fields:
            all_tasks.extend(
                t for t in field.tasks
                if t.task_category == 'field' and not t.completed
            )
        unique_tasks = list({t.id: t for t in all_tasks}.values())
        return {"fields": fields, "tasks": unique_tasks}

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
    def get_vocabulary() -> dict:
        soil_types = [{"id": s.id, "name": s.name} for s in Soil_Type.query.order_by(Soil_Type.name).all()]
        water_sources = [{"id": w.id, "name": w.name} for w in WaterSource.query.order_by(WaterSource.name).all()]
        return {"soil_types": soil_types, "water_sources": water_sources}

    @staticmethod
    def get_fields_by_user(user_id: int):
        return FieldRepository.get_by_user_id(user_id)

    @staticmethod
    def get_field_summary(field_id):
        field = FieldRepository.get_by_id(field_id)
        if not field:
            return None
        return {
            "id": field.id,
            "name": field.name,
            "acreage": field.acreage,
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
