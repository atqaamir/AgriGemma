import json
import logging
from datetime import datetime

from app.extensions import db
from app.models.task import Task
from app.repositories.task_repository import TaskRepository
from app.services.plan_override_service import PlanOverrideService
from app.utils import clock

logger = logging.getLogger(__name__)

PLAN_TASK_CATEGORY = "plan"
PLAN_OWNED_FIELDS = ("due_date", "task_type", "task_category")


class TaskService:

    @staticmethod
    def create_task(data: dict) -> Task:
        return TaskRepository.create(data)

    @staticmethod
    def record_changes(task: Task, changes: list, updates: dict) -> Task:
        """Apply `updates` to a task and append `changes` to its history (task_changes).

        Each change gets "changed_on" = clock.today() (the demo date); the task's
        changed_on column is set too, so change notifications can pick today's
        changes. created_at is never touched.
        """
        today = clock.today()
        try:
            history = json.loads(task.task_changes) if task.task_changes else []
        except (TypeError, ValueError):
            history = []
        if isinstance(history, dict):
            history = [history]
        history += [{**c, "changed_on": today.isoformat()} for c in changes]
        return TaskRepository.update(task, {**updates, "task_changes": json.dumps(history), "changed_on": today})

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
            # Delete = un-complete: drop this task's farmer_completed overrides first,
            # so dates fall back to the forecast / seasonal plan.
            PlanOverrideService.undo_farmer_task(task)
            TaskRepository.delete(task)

    @staticmethod
    def update_task(task_id: int, data: dict):
        task = TaskRepository.get_by_id(task_id)
        if not task:
            return None

        if task.task_category == PLAN_TASK_CATEGORY:
            # The weekly plan owns these (sync_plan_tasks is the only thing that changes them);
            # completing, notes, title, priority and description stay editable.
            ignored = sorted(k for k in PLAN_OWNED_FIELDS if k in data)
            if ignored:
                logger.info("Task %s is a plan task: ignoring %s", task.id, ignored)
                data = {k: v for k, v in data.items() if k not in PLAN_OWNED_FIELDS}

        was_completed = bool(task.completed)
        now_completed = bool(data.get("completed", was_completed))
        if now_completed and not was_completed:
            data = {**data, "completed_at": clock.now()}
        elif was_completed and not now_completed:
            data = {**data, "completed_at": None}

        task = TaskRepository.update(task, data)

        # Farmer completion of a sowing task → actual-dates layer. The task update
        # itself is already saved; an override problem is logged, not raised.
        if now_completed != was_completed and task.task_type in PlanOverrideService.SOWING_TASK_TYPES:
            try:
                if now_completed:
                    PlanOverrideService.record_farmer_sowing(task)
                else:
                    PlanOverrideService.undo_farmer_task(task)
            except Exception:
                db.session.rollback()
                logger.exception("Task %s: updating farmer_completed overrides failed", task.id)
        return task

    @staticmethod
    def get_pending_tasks() -> list:
        """All incomplete tasks, sorted: critical → high → medium → low, then by due date."""
        return TaskRepository.get_pending()

    @staticmethod
    def get_pending_tasks_by_user(user_id: int) -> list:
        """All incomplete tasks for a specific user."""
        tasks = TaskRepository.get_by_user_id(user_id)
        return [t for t in tasks if not t.completed]

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
    def get_tasks_by_user_paginated(
        user_id: int,
        page: int = 1,
        per_page: int = 20,
        status: str = "all",
        search: str = "",
        priority: str = None,
    ):
        """Paginated task list for a specific user with optional filters."""
        query = TaskRepository.get_all().filter(Task.user_id == user_id)

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
    def count_pending_by_user(user_id: int) -> int:
        """Count incomplete tasks for a specific user."""
        return TaskRepository.get_all().filter(Task.user_id == user_id, Task.completed.is_(False)).count()

    @staticmethod
    def count_completed() -> int:
        return TaskRepository.count_completed()

    @staticmethod
    def count_completed_by_user(user_id: int) -> int:
        """Count completed tasks for a specific user."""
        return TaskRepository.get_all().filter(Task.user_id == user_id, Task.completed.is_(True)).count()

    @staticmethod
    def get_pending_tasks_for_crop(crop_id: int) -> list:
        return TaskRepository.get_all().filter_by(crop_id=crop_id, completed=False).all()

    @staticmethod
    def get_tasks_by_user(user_id: int) -> list:
        return TaskRepository.get_by_user_id(user_id)

    @staticmethod
    def get_tasks_for_field(field_id: int) -> list:
        return TaskRepository.get_all().filter_by(field_id=field_id, completed=False).all()
