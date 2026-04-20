from app.models.field import Field
from app.extensions import db

class TaskRepository:

    @staticmethod
    def create(data):
        task = Task(**data)
        db.session.add(task)
        db.session.commit()
        return task

    @staticmethod
    def get_all():
        return Task.query

    @staticmethod
    def get_by_id(task_id):
        return Task.query.get(task_id)

    @staticmethod
    def delete(task):
        db.session.delete(task)
        db.session.commit()

    @staticmethod
    def update(task, data):    
        for key, value in data.items():
            setattr(task, key, value)
        db.session.commit()
        return task