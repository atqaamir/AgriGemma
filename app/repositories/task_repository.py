from app.models.task import Task
from app.extensions import db


class TaskRepository:

    @staticmethod
    def create(data: dict) -> Task:
        task = Task(**data)
        db.session.add(task)
        db.session.commit()
        return task

    @staticmethod
    def get_all():
        """Returns a base query — callers may chain .filter(), .paginate(), etc."""
        return Task.query

    @staticmethod
    def get_by_id(task_id: int):
        return Task.query.get(task_id)

    @staticmethod
    def get_pending() -> list:
        return (
            Task.query
            .filter_by(completed=False)
            .order_by(
                db.case(
                    (Task.priority == "critical", 0),
                    (Task.priority == "high", 1),
                    (Task.priority == "medium", 2),
                    else_=3,
                ),
                Task.due_date.asc().nullslast(),
            )
            .all()
        )

    @staticmethod
    def get_all_field_tasks() -> list:
        return Task.query.filter_by(task_category="field").all()

    @staticmethod
    def get_pending_field_tasks() -> list:
        return Task.query.filter_by(task_category="field", completed=False).all()

    @staticmethod
    def get_pending_tasks_by_field_id(field_id: int) -> list:
        return Task.query.filter_by(field_id=field_id, completed=False).all()

    @staticmethod
    def get_tasks_by_field_id(field_id: int) -> list:
        return Task.query.filter_by(field_id=field_id).all()

    @staticmethod
    def count_pending() -> int:
        return Task.query.filter_by(completed=False).count()

    @staticmethod
    def count_completed() -> int:
        return Task.query.filter_by(completed=True).count()

    @staticmethod
    def delete(task: Task) -> None:
        db.session.delete(task)
        db.session.commit()

    @staticmethod
    def update(task: Task, data: dict) -> Task:
        for key, value in data.items():
            setattr(task, key, value)
        db.session.commit()
        return task
