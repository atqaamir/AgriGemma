def generate_tasks(weather, crop, soil):
    tasks = []

    if weather.get("rain_expected"):
        tasks.append({"title": "Delay irrigation", "priority": "high"})

    if weather.get("heatwave_risk"):
        tasks.append({"title": "Irrigate early morning to reduce heat stress", "priority": "high"})

    if crop.get("growth_stage") == "growth":
        tasks.append({"title": "Apply fertilizer", "priority": "medium"})

    if crop.get("growth_stage") == "flowering":
        tasks.append({"title": "Monitor crop for pests and stress", "priority": "medium"})

    moisture = soil.get("moisture_percent", 50)
    soil_temp = soil.get("temperature_c", 25)

    if moisture < 30:
        tasks.append({"title": "Irrigate field (low soil moisture)", "priority": "high"})

    if moisture > 80:
        tasks.append({"title": "Check drainage (soil too wet)", "priority": "medium"})

    if soil_temp > 35:
        tasks.append({"title": "Monitor root stress due to high soil temperature", "priority": "medium"})

    unique_tasks = []
    seen = set()
    for task in tasks:
        if task["title"] not in seen:
            unique_tasks.append(task)
            seen.add(task["title"])

    return unique_tasks


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
    def get_notifications_for_user(user_id):
        pass
       

    @staticmethod
    def get_critical_alert_for_user(user_id):
       pass
