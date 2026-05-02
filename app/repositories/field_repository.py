from sqlalchemy.orm import subqueryload

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
        # subqueryload prevents N+1 when iterating fields and accessing field.crops or field.tasks
        return Field.query.options(
            subqueryload(Field.crops),
            subqueryload(Field.tasks),
        ).all()

    @staticmethod
    def get_all_active():
        return Field.query.options(
            subqueryload(Field.crops),
            subqueryload(Field.tasks),
        ).filter_by(currently_active=True).all()

    @staticmethod
    def get_by_id(field_id):
        return Field.query.options(
            subqueryload(Field.crops),
            subqueryload(Field.tasks),
        ).get(field_id)

    @staticmethod
    def get_pending_tasks_by_field_id(field_id):
        from app.models.task import Task
        return Task.query.filter_by(field_id=field_id, completed=False).all()

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

    @staticmethod
    def get_by_user_id(user_id):
        return Field.query.options(
            subqueryload(Field.crops),
            subqueryload(Field.tasks),
        ).filter_by(user_id=user_id).all()
