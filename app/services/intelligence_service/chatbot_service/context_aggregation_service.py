import logging
from datetime import date

from app.repositories.field_repository import FieldRepository
from app.repositories.task_repository import TaskRepository

logger = logging.getLogger(__name__)


class ContextAggregationService:
    """
    Aggregates all farm context required by the task intelligence pipeline.
    Every data source is fetched defensively so a single failure cannot
    prevent the rest of the context from being collected.
    """

    @staticmethod
    def build_task_context(user_id: int) -> dict:
        today = date.today()

        field_ctx = ContextAggregationService._collect_field_context()
        crop_ctx = ContextAggregationService._collect_crop_context()
        task_ctx = ContextAggregationService._collect_task_context(today)
        alert_ctx = ContextAggregationService._collect_alert_context(field_ctx.get("_active_fields", []))
        weather_ctx = ContextAggregationService._collect_weather_context(user_id)
        farmer_name = ContextAggregationService._collect_farmer_name(user_id)
        rules_ctx = ContextAggregationService._collect_rules_context(
            crop_ctx["active_data"], weather_ctx
        )
        seasonal_plan = ContextAggregationService._collect_seasonal_plan(user_id)
        weekly_plan = ContextAggregationService._collect_weekly_plan(user_id)
        climate_ctx = ContextAggregationService._collect_climate_context(user_id)

        return {
            "farmer_name": farmer_name,
            "farm": {
                "total_fields": field_ctx["total"],
                "active_fields": field_ctx["active"],
                "total_crops": crop_ctx["total"],
                "active_fields_data": field_ctx["active_data"],
                "active_crops_data": crop_ctx["active_data"],
            },
            "tasks": task_ctx,
            "alerts": alert_ctx,
            "weather": weather_ctx,
            "climate": climate_ctx,
            "rules": rules_ctx,
            "seasonal_plan": seasonal_plan,
            "weekly_plan": weekly_plan,
        }

    # ── Private collectors ────────────────────────────────────────────────────

    @staticmethod
    def _collect_rules_context(active_crops_data: list, weather_ctx: dict) -> str:
        try:
            from app.services.rules_context_service import RulesContextService
            return RulesContextService.build_for_crops(active_crops_data, weather_ctx)
        except Exception as exc:
            logger.warning("ContextAggregationService: rules context failed — %s", exc)
            return ""

    @staticmethod
    def _collect_farmer_name(user_id: int) -> str:
        try:
            from app.services.domain_service.user_service import UserService
            user = UserService.get_user_by_id(user_id)
            return user.name if user and user.name else "Farmer"
        except Exception:
            return "Farmer"

    @staticmethod
    def _collect_field_context() -> dict:
        try:
            all_fields = FieldRepository.get_all()
            active_fields = FieldRepository.get_all_active()
            return {
                "total": len(all_fields),
                "active": len(active_fields),
                "_active_fields": active_fields,
                "active_data": [
                    {
                        "id": f.id,
                        "name": f.name,
                        "health_status": f.health_status,
                        "moisture_level": f.moisture_level,
                        "heat_level": f.heat_level,
                        "stress_risk": f.stress_risk,
                        "disease_risk": f.disease_risk,
                        "field_score": f.field_score,
                        "currently_active": f.currently_active,
                    }
                    for f in active_fields
                ],
            }
        except Exception as exc:
            logger.warning("ContextAggregationService: field collection failed — %s", exc)
            return {"total": 0, "active": 0, "_active_fields": [], "active_data": []}

    @staticmethod
    def _collect_crop_context() -> dict:
        try:
            from app.services.domain_service.crop_service import CropService
            active_crops = CropService.get_active_crops()
            return {
                "total": len(active_crops),
                "active_data": [
                    {
                        "id": c.id,
                        "name": c.name,
                        "growth_stage": c.growth_stage,
                        "health_status": c.current_health_status,
                        "water_requirement": c.currently_water_requirement,
                        # IDs needed for rulebook lookups
                        "crop_name_id": c.crop_name_id,
                        "growth_stage_id": c.current_growth_stage_id,
                        "soil_type_id": c.field.soil_type_id if c.field else None,
                        "moisture_level": c.field.moisture_level if c.field else None,
                        "field_name": c.field.name if c.field else None,
                    }
                    for c in active_crops
                ],
            }
        except Exception as exc:
            logger.warning("ContextAggregationService: crop collection failed — %s", exc)
            return {"total": 0, "active_data": []}

    @staticmethod
    def _collect_task_context(today: date) -> dict:
        try:
            pending = TaskRepository.get_pending()
            all_query = TaskRepository.get_all()
            total = all_query.count()

            overdue = [t for t in pending if t.due_date and t.due_date < today]
            critical = [t for t in pending if t.priority == "critical"]
            high = [t for t in pending if t.priority == "high"]

            return {
                "total": total,
                "pending_count": len(pending),
                "overdue_count": len(overdue),
                "critical_count": len(critical),
                "high_priority_count": len(high),
                # Cap at 25 tasks to keep the prompt at a manageable size
                "pending_list": [
                    {
                        "id": t.id,
                        "title": t.title,
                        "priority": t.priority,
                        "task_type": t.task_type,
                        "task_category": t.task_category,
                        "due_date": str(t.due_date) if t.due_date else None,
                        "field_name": t.field.name if t.field else None,
                        "crop_name": t.crop.name if t.crop else None,
                        "is_overdue": bool(t.due_date and t.due_date < today),
                        "description": t.description,
                    }
                    for t in pending[:25]
                ],
            }
        except Exception as exc:
            logger.warning("ContextAggregationService: task collection failed — %s", exc)
            return {
                "total": 0,
                "pending_count": 0,
                "overdue_count": 0,
                "critical_count": 0,
                "high_priority_count": 0,
                "pending_list": [],
            }

    @staticmethod
    def _collect_alert_context(active_fields: list) -> list:
        try:
            from app.services.domain_service.notification_service import NotificationService
            alert_service = NotificationService()
            alerts = []
            for field in active_fields:
                alerts.extend(alert_service.get_active_alerts(field.id))
            # Deduplicate by message
            seen, unique = set(), []
            for a in alerts:
                msg = a.get("message", "")
                if msg not in seen:
                    unique.append(a)
                    seen.add(msg)
            return unique
        except Exception as exc:
            logger.warning("ContextAggregationService: alert collection failed — %s", exc)
            return []

    @staticmethod
    def _collect_weather_context(user_id: int) -> dict:
        try:
            from app.services.weather_service.forecast_service import ForecastService
            return ForecastService.get_current_summary(user_id) or {}
        except Exception:
            return {}

    @staticmethod
    def _collect_climate_context(user_id: int) -> dict:
        try:
            from app.services.weather_service.forecast_service import ForecastService
            return ForecastService.get_climate_context(user_id) or {}
        except Exception as exc:
            logger.warning("ContextAggregationService: climate context failed — %s", exc)
            return {}

    @staticmethod
    def _collect_seasonal_plan(user_id: int) -> dict:
        try:
            from app.services.seasonal_planner_service import SeasonalPlannerService
            plan = SeasonalPlannerService.get_active_plan(user_id)
            if not plan:
                return {}
            return {
                "growth_stage_id": plan.growth_stage_id,
                "currently_active": plan.currently_active,
                "entries": [
                    {
                        "crop_id":               e.crop_name_id,
                        "soil_type_id":          e.soil_id,
                        "water_source_id":       e.water_source_id,
                        "sowing":                e.sowing,
                        "harvesting":            e.harvesting,
                        "irrigation_start_date": e.irrigation_start_date,
                        "irrigation_frequency":  e.irrigation_frequency,
                        "fertilization_date":    e.fertilization_date,
                        "adjustments_to_make":   e.adjustments_to_make,
                    }
                    for e in (plan.entries or [])
                ],
            }
        except Exception as exc:
            logger.warning("ContextAggregationService: seasonal plan collection failed — %s", exc)
            return {}

    @staticmethod
    def _collect_weekly_plan(user_id: int) -> dict:
        try:
            from app.services.weekly_planning_service.weekly_planner_service import WeeklyPlannerService
            return WeeklyPlannerService().get_active_plan(user_id) or {}
        except Exception as exc:
            logger.warning("ContextAggregationService: weekly plan collection failed — %s", exc)
            return {}
