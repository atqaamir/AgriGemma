from app.models.field import Field
from app.extensions import db

class FieldRepository:

    @staticmethod
    def create(data):
        field = Field(**data)
        db.session.add(field)
        db.session.commit()
        return field

    @staticmethod
    def get_all():
        return Field.query.all()

    @staticmethod
    def get_by_id(field_id):
        return Field.query.get(field_id)

    @staticmethod
    def delete(field):
        db.session.delete(field)
        db.session.commit()

    @staticmethod
    def update(field, data):    
        for key, value in data.items():
            setattr(field, key, value)
        db.session.commit()
        return field