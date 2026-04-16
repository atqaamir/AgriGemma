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
        field = fieldRepository.get_by_id(field_id)
        if field:
            fieldRepository.delete(field)
        return field

    def get_field_status(field):
        if field.health_status == "good":
            return "Healthy"
        elif field.health_status == "warning":
            return "Needs attention"
        return "At risk"

    def get_field_disease_status(field):
        pass

    def get_field_heat_status(field):
        pass

    def get_field_moisture_status(field):
        pass

    def get_field_soil_status(field):
        pass

    def get_field_health_status(field):
        pass

    def get_currently_active_fields():
        return FieldRepository.get_all().filter_by(currently_active=True)