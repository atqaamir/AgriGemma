from datetime import date

from app.services.domain_service.user_service import UserService
from app.services.domain_service.field_service import FieldService
from app.services.domain_service.crop_service import CropService
from app.services.domain_service.task_service import TaskService
from app.services.domain_service.notification_service import NotificationService
from app.services.intelligence_service.chatbot_service.chatbot_service import ChatbotService
from app.services.intelligence_service.task_intelligence_service import TaskIntelligenceService
from app.services.intelligence_service.chatbot_service.context_aggregation_service import ContextAggregationService


def _avg(values: list) -> float:
    return round(sum(values) / len(values), 1) if values else 0.0


class DashboardService:

    @staticmethod
    def build_dashboard_data(user_id: int) -> dict:

        user = UserService.get_user_by_id(user_id)

        fields = FieldService.get_fields_by_user(user_id)
        active_fields = [f for f in fields if f.currently_active]

        # Crops are subqueryloaded on fields — avoid a second round-trip
        crops = [c for f in fields for c in f.crops if c.currently_active]

        tasks = TaskService.get_tasks_by_user(user_id)
        pending_tasks = [t for t in tasks if not t.completed]
        context = ContextAggregationService.build_task_context(user_id)
        ai_insights = TaskIntelligenceService.generate_intelligence(context, user_id)

        return {
            "user": DashboardService._build_user_section(user),
            "weather": DashboardService._build_weather_section(active_fields),
            "overview": DashboardService._build_farm_overview(
                fields,
                active_fields,
                crops,
                tasks,
                pending_tasks,
            ),
            "critical_tasks": DashboardService._get_critical_tasks(pending_tasks),
            "soil_condition": DashboardService._build_soil_condition(active_fields),
            "field_condition": DashboardService._build_field_condition(fields, active_fields),
            "crop_condition": DashboardService._build_crop_condition(crops),
            "alerts": DashboardService._get_alerts(user_id, pending_tasks),
            "insights": ai_insights.get("insights", []),
            "dashboard_summary": ai_insights.get("summary"),
            "dashboard_recommendations": ai_insights.get("recommendations", []),
            "seasonal_plan": DashboardService._build_plan_summary(user_id),
        }
    
    @staticmethod
    def _build_user_section(user):
        return {
            "id": user.id,
            "name": user.name,
        }

    @staticmethod
    def _build_weather_section(active_fields):

        if not active_fields:

            return {}

        return {
            "current": {
                "temperature_c": 32,
                "condition": "Sunny",
            },

            "forecast": [
                {
                    "day": "Tue",
                    "temperature_c": 30,
                    "condition": "Cloudy",
                },
                {
                    "day": "Wed",
                    "temperature_c": 26,
                    "condition": "Rainy",
                },
                 {
                    "day": "Thu",
                    "temperature_c": 28,
                    "condition": "Rainy",
                },
            ]
        }
    
    @staticmethod
    def _get_alerts(user_id, tasks):
        """Return unread notifications in a serializable form."""
        alerts = NotificationService.get_unread(user_id)
        return [
            {
                "id": alert.id,
                "title": alert.title,
                "message": alert.message,
                "detail": alert.detail,
                "notification_type": alert.notification_type,
                "created_at": alert.created_at.isoformat() if getattr(alert, "created_at", None) else None,
            }
            for alert in alerts
        ]


    @staticmethod
    def chat_with_advisor(user_id: int, message: str) -> str:
        # TODO: pass user_id context once ChatbotService supports user-scoped sessions
        return ChatbotService.get_chat_response(message)

    @staticmethod
    def refresh_dashboard(user_id: int) -> dict:
        return DashboardService.build_dashboard_data(user_id)

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
        high_priority = [t for t in pending_tasks if t.priority in ("critical", "high")]
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
            key = (crop.current_health_status or "").lower()
            status_counts[key] = status_counts.get(key, 0) + 1
        return {
            "total": len(all_crops),
            "healthy": status_counts.get("healthy", 0),
            "warning": status_counts.get("alert", 0),
            "at_risk": status_counts.get("critical", 0),
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

    @staticmethod
    def _build_ai_insights(weather, tasks):
        return {
            "summary": "Irrigation demand likely to increase over next 3 days due to heat buildup."
        }

    @staticmethod
    def _build_plan_summary(user_id: int) -> dict:
        from app.services.seasonal_planner_service import SeasonalPlannerService

        plan = SeasonalPlannerService.get_active_plan(user_id)
        if not plan:
            return {}
        return {
            "id":              plan.id,
            "growth_stage_id": plan.growth_stage_id,
            "currently_active": plan.currently_active,
            "entries": [
                {
                    "crop_id":              e.crop_id,
                    "soil_type_id":         e.soil_type_id,
                    "water_source_id":      e.water_source_id,
                    "sowing":               e.sowing,
                    "harvesting":           e.harvesting,
                    "irrigation_start_date": e.irrigation_start_date,
                    "irrigation_frequency": e.irrigation_frequency,
                    "fertilization_date":   e.fertilization_date,
                    "adjustments_to_make":  e.adjustments_to_make,
                }
                for e in (plan.entries or [])
            ],
        }
  