import logging
import math
from datetime import date

from app.services.domain_service.user_service import UserService
from app.services.domain_service.field_service import FieldService
from app.services.domain_service.crop_service import CropService
from app.services.domain_service.task_service import TaskService
from app.services.domain_service.notification_service import NotificationService
from app.utils import clock


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

        # Cancelled (deactivated) tasks are left out of every dashboard number.
        tasks = [t for t in TaskService.get_tasks_by_user(user_id) if t.is_active]
        pending_tasks = [t for t in tasks if not t.completed]

        return {
            "user": DashboardService._build_user_section(user),
            "weather": DashboardService._build_weather_section(user_id),
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
            # Latest stored farm report + whether the farm changed since (no AI call here).
            "farm_report": DashboardService._farm_report(user_id),
            "seasonal_plan": DashboardService._build_plan_summary(user_id),
        }

    @staticmethod
    def _farm_report(user_id: int) -> dict | None:
        from app.services import insight_report_service as reports
        try:
            return reports.payload(user_id, "farm_report")
        except Exception:            # the dashboard must load even if the report can't be read
            logging.getLogger(__name__).exception("Farm report payload failed for user %s", user_id)
            return None

    @staticmethod
    def _build_user_section(user):
        return {
            "id": user.id,
            "name": user.name,
        }

    @staticmethod
    def _build_weather_section(user_id: int) -> dict:
        """Weather card from the forecast table (the forecast the weekly plan and the chatbot
        use, demo date via the clock): today's daily average + the next 3 days. No rows → {}
        (the card shows "--"), never made-up numbers."""
        from app.services.weather_service.forecast_service import ForecastService
        summary = ForecastService._summary_from_forecast_table(user_id)
        days = summary.get("forecast") or []
        if not days:
            return {}

        def temp(day):
            return math.floor(day["avg_temp_c"] + 0.5) if day.get("avg_temp_c") is not None else None   # half up

        today = days[0]
        return {
            "current": {"temperature_c": temp(today), "condition": today["condition"], "date": today["date"]},
            "forecast": [
                {"day": date.fromisoformat(d["date"]).strftime("%a"), "date": d["date"],
                 "temperature_c": temp(d), "condition": d["condition"], "rain_mm": d.get("rain_mm")}
                for d in days[1:4]
            ],
            "source": "forecast table (daily average)",
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
    def refresh_dashboard(user_id: int) -> dict:
        return DashboardService.build_dashboard_data(user_id)

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
        today = clock.today()
        priority_order = {"critical": 0, "high": 1}

        def sort_key(task):
            p = priority_order.get(task.priority or "high", 1)
            if task.due_date is None:
                return (p, 2, date.max)
            if task.due_date < today:
                return (p, 0, task.due_date)
            return (p, 1, task.due_date)

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
            "overdue": bool(task.due_date and task.due_date < clock.today()),
        }

    @staticmethod
    def _build_plan_summary(user_id: int) -> dict:
        from app.services.seasonal_planner_service import SeasonalPlannerService
        plan = SeasonalPlannerService.get_active_plan(user_id)
        if not plan:
            return {}
        return {
            "id":               plan.id,
            "currently_active": plan.currently_active,
        }

