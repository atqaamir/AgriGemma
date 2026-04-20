from app.repositories.field_repository import FieldRepository


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
    def get_field_status(field):
        if field.health_status == "good":
            return "Healthy"
        elif field.health_status == "warning":
            return "Needs attention"
        return "At risk"

    @staticmethod
    def get_field_disease_status(field):
        pass

    @staticmethod
    def get_field_heat_status(field):
        pass

    @staticmethod
    def get_field_moisture_status(field):
        pass

    @staticmethod
    def get_field_soil_status(field):
        pass

    @staticmethod
    def get_field_health_status(field):
        pass

    @staticmethod
    def get_currently_active_fields():
        fields = FieldRepository.get_all()

        # If repository returns a SQLAlchemy query
        if hasattr(fields, "filter_by"):
            return fields.filter_by(currently_active=True).all()

        # If repository returns a Python list
        return [field for field in fields if field.currently_active]

    @staticmethod
    def get_active_fields_with_tasks():
        fields = FieldService.get_currently_active_fields()

        all_tasks = []
        seen_task_ids = set()

        for field in fields:
            for task in field.tasks:
                if task.id not in seen_task_ids:
                    seen_task_ids.add(task.id)
                    all_tasks.append(task)

        return {
            "fields": fields,
            "tasks": all_tasks,
        }