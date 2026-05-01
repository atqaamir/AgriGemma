from app.models.task import Task
from app.repositories.task_repository import TaskRepository


class TaskService:

    @staticmethod
    def create_task(data: dict) -> Task:
        return TaskRepository.create(data)

    @staticmethod
    def get_all_tasks():
        """Returns a base SQLAlchemy query for further chaining."""
        return TaskRepository.get_all()

    @staticmethod
    def get_task_by_id(task_id: int):
        return TaskRepository.get_by_id(task_id)

    @staticmethod
    def delete_task(task_id: int) -> None:
        task = TaskRepository.get_by_id(task_id)
        if task:
            TaskRepository.delete(task)

    @staticmethod
    def update_task(task_id: int, data: dict):
        task = TaskRepository.get_by_id(task_id)
        if not task:
            return None
        return TaskRepository.update(task, data)

    @staticmethod
    def get_pending_tasks() -> list:
        """All incomplete tasks, sorted: critical → high → medium → low, then by due date."""
        return TaskRepository.get_pending()

    @staticmethod
    def get_tasks_paginated(
        page: int = 1,
        per_page: int = 20,
        status: str = "all",
        search: str = "",
        priority: str = None,
    ):
        """Paginated task list with optional filters."""
        query = TaskRepository.get_all()

        if status == "pending":
            query = query.filter(Task.completed.is_(False))
        elif status == "completed":
            query = query.filter(Task.completed.is_(True))

        if search:
            query = query.filter(Task.title.ilike(f"%{search}%"))

        if priority:
            query = query.filter(Task.priority == priority)

        return query.order_by(Task.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

    @staticmethod
    def count_pending() -> int:
        return TaskRepository.count_pending()

    @staticmethod
    def count_completed() -> int:
        return TaskRepository.count_completed()

    @staticmethod
    def get_pending_tasks_for_crop(crop_id: int) -> list:
        return TaskRepository.get_all().filter_by(crop_id=crop_id, completed=False).all()

    @staticmethod
    def get_tasks_for_field(field_id: int) -> list:
        return TaskRepository.get_all().filter_by(field_id=field_id, completed=False).all()
