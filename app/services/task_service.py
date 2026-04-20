def generate_tasks(weather, crop, soil):
    tasks = []

    # 🌧️ Weather-based tasks
    if weather.get("rain_expected"):
        tasks.append({
            "title": "Delay irrigation",
            "priority": "high"
        })

    if weather.get("heatwave_risk"):
        tasks.append({
            "title": "Irrigate early morning to reduce heat stress",
            "priority": "high"
        })

    # 🌱 Crop-based tasks
    if crop.get("growth_stage") == "growth":
        tasks.append({
            "title": "Apply fertilizer",
            "priority": "medium"
        })

    if crop.get("growth_stage") == "flowering":
        tasks.append({
            "title": "Monitor crop for pests and stress",
            "priority": "medium"
        })

    # 🌾 Soil-based tasks (NEW)
    moisture = soil.get("moisture_percent", 50)
    soil_temp = soil.get("temperature_c", 25)

    if moisture < 30:
        tasks.append({
            "title": "Irrigate field (low soil moisture)",
            "priority": "high"
        })

    if moisture > 80:
        tasks.append({
            "title": "Check drainage (soil too wet)",
            "priority": "medium"
        })

    if soil_temp > 35:
        tasks.append({
            "title": "Monitor root stress due to high soil temperature",
            "priority": "medium"
        })

    # 🧠 Optional: avoid duplicates
    unique_tasks = []
    seen = set()

    for task in tasks:
        if task["title"] not in seen:
            unique_tasks.append(task)
            seen.add(task["title"])

    return unique_tasks



from app.repositories.task_repository import TaskRepository

class TaskService:
    def __init__(self):
        self.repository = TaskRepository()

    def create_tasks(self, data):
        return self.repository.create(data)

    def get_all_tasks(self):
        return self.repository.get_all()

    def get_task_by_id(self, task_id):
        print (f"Fetching task with ID: {task_id} from repository")
        return self.repository.get_by_id(task_id)

    def delete_task(self, task):
        self.repository.delete(task)

    def update_tasks(self, task, data):
        return self.repository.update(task, data)