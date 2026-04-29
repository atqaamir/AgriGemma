from datetime import date

from app.services.domain_service.user_service import UserService
from app.services.domain_service.field_service import FieldService
from app.services.domain_service.crop_service import CropService
from app.services.domain_service.task_service import TaskService
from app.services.intelligence_service.chatbot_service.chatbot_service import ChatbotService


def _avg(values: list) -> float:
    return round(sum(values) / len(values), 1) if values else 0.0


class DashboardService:

    @staticmethod
    def build_dashboard_data(user_id: int) -> dict:
        user = UserService.get_user_by_id(user_id)
        username = user.name if user else "Farmer"

        all_fields = list(FieldService.get_all_fields())
        active_fields = list(FieldService.get_currently_active_fields())
        all_crops = list(CropService.get_all_crops())
        all_tasks = list(TaskService.get_all_tasks())
        pending_tasks = [t for t in all_tasks if not t.completed]

        return {
            "username": username,
            "farm_overview": DashboardService._build_farm_overview(
                all_fields, active_fields, all_crops, all_tasks, pending_tasks
            ),
            "critical_tasks": DashboardService._get_critical_tasks(pending_tasks),
            "soil_condition": DashboardService._build_soil_condition(active_fields),
            "field_condition": DashboardService._build_field_condition(all_fields, active_fields),
            "crop_condition": DashboardService._build_crop_condition(all_crops),
        }
    
    @staticmethod
    def chat_with_advisor(user_id: int, message: str) -> str:
        # use user_id to get context later
        return ChatbotService.get_chat_response(message) 

    @staticmethod
    def generate_seasonal_plan(user_id: int) -> dict:
        # Placeholder for future implementation
        return {
            "plan": "This feature is under development. It will provide a detailed seasonal plan based on your farm's data and local conditions."
        }


    @staticmethod
    def _build_farm_overview(all_fields, active_fields, all_crops, all_tasks, pending_tasks) -> dict:
        return {
            "total_fields": len(all_fields),
            "active_fields": len(active_fields),
            "total_acreage": round(sum(f.acreage or 0.0 for f in all_fields), 2),
            "total_crops": len(all_crops),
            "total_tasks": len(all_tasks),
            "pending_tasks": len(pending_tasks),
            "completed_tasks": len(all_tasks) - len(pending_tasks),
        }

    @staticmethod
    def _get_critical_tasks(pending_tasks) -> list:
        high_priority = [t for t in pending_tasks if t.priority == "high"]
        today = date.today()

        def sort_key(task):
            if task.due_date is None:
                return (2, date.max)
            if task.due_date < today:
                return (0, task.due_date)
            return (1, task.due_date)

        return [
            DashboardService._serialize_task(t)
            for t in sorted(high_priority, key=sort_key)
        ]

    @staticmethod
    def _build_soil_condition(active_fields) -> dict:
        moisture = [f.moisture_level for f in active_fields if f.moisture_level is not None]
        heat = [f.heat_level for f in active_fields if f.heat_level is not None]
        stress = [f.stress_risk for f in active_fields if f.stress_risk is not None]
        return {
            "avg_moisture": _avg(moisture),
            "avg_heat": _avg(heat),
            "avg_stress": _avg(stress),
            "low_moisture_fields": sum(1 for v in moisture if v < 30),
            "high_stress_fields": sum(1 for v in stress if v >= 60),
            "fields_sampled": len(active_fields),
        }

    @staticmethod
    def _build_field_condition(all_fields, active_fields) -> dict:
        scores = [f.field_score for f in all_fields if f.field_score is not None]
        status_counts: dict[str, int] = {}
        for field in all_fields:
            key = (field.health_status or "").lower()
            status_counts[key] = status_counts.get(key, 0) + 1
        return {
            "total": len(all_fields),
            "active": len(active_fields),
            "inactive": len(all_fields) - len(active_fields),
            "healthy": status_counts.get("healthy", 0),
            "alert": status_counts.get("alert", 0),
            "critical": status_counts.get("critical", 0),
            "avg_score": _avg(scores),
        }

    @staticmethod
    def _build_crop_condition(all_crops) -> dict:
        status_counts: dict[str, int] = {}
        for crop in all_crops:
            key = (crop.health_status or "").lower()
            status_counts[key] = status_counts.get(key, 0) + 1
        return {
            "total": len(all_crops),
            "healthy": status_counts.get("healthy", 0),
            "warning": status_counts.get("warning", 0),
            "at_risk": status_counts.get("risk", 0),
            "needing_irrigation": sum(
                1 for c in all_crops if CropService.needs_irrigation(c)
            ),
        }

    @staticmethod
    def _serialize_task(task) -> dict:
        return {
            "id": task.id,
            "title": task.title,
            "priority": task.priority,
            "task_type": task.task_type,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "field_name": task.field.name if task.field else None,
            "crop_name": task.crop.name if task.crop else None,
            "overdue": bool(task.due_date and task.due_date < date.today()),
        }
