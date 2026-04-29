from app.repositories.task_repository import TaskRepository


class TaskService:

    @staticmethod
    def create_task(data):
        return TaskRepository.create(data)

    @staticmethod
    def get_all_tasks():
        return TaskRepository.get_all()

    @staticmethod
    def get_task_by_id(task_id):
        return TaskRepository.get_by_id(task_id)

    @staticmethod
    def delete_task(task_id):
        task = TaskRepository.get_by_id(task_id)
        if task:
            TaskRepository.delete(task)

    @staticmethod
    def update_task(task_id, data):
        task = TaskRepository.get_by_id(task_id)
        if not task:
            return None
        return TaskRepository.update(task, data)

    @staticmethod
    def get_pending_tasks_for_crop(crop_id):
        """get all tasks associated with a specific crop"""
        return TaskRepository.get_all().filter_by(crop_id=crop_id, completed=False).all()

    @staticmethod
    def get_tasks_for_field(field_id):
        """get all tasks associated with a specific field where completed is false"""
        return TaskRepository.get_all().filter_by(field_id=field_id, completed=False).all()

    # @staticmethod
    # def 
