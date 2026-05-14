from datetime import datetime

from app.services.domain_service.field_service import FieldService
from app.services.domain_service.task_service import TaskService
from app.services.intelligence_service.task_intelligence_service import TaskIntelligenceService
from app.services.intelligence_service.chatbot_service.context_aggregation_service import ContextAggregationService
from app.services.seasonal_planner_service import SeasonalPlannerService
from app.services.weather_service.weekly_planner_service import WeeklyPlannerService
from app.repositories.task_repository import TaskRepository


class TaskGenerationService:
    def __init__(self):
        pass

    def generate_daily_tasks(self, user_id: int) -> dict:
        fields = FieldService.get_fields_by_user(user_id) or []
        weekly_plan = WeeklyPlannerService().get_active_weekly_plan(user_id) or {}
        seasonal_plan = SeasonalPlannerService.get_active_plan(user_id) or {}
        existing_titles = {
            task.title for task in TaskService.get_tasks_by_user(user_id) or [] if not task.completed
        }

        context = ContextAggregationService.build_task_context(user_id)
        created_tasks = []

        for field in [f for f in fields if getattr(f, "currently_active", False)]:
            if field.moisture_level is not None and field.moisture_level < 30:
                title = f"Irrigate {field.name}"
                if title not in existing_titles:
                    data = {
                        "title": title,
                        "priority": "high",
                        "task_type": "irrigation",
                        "task_category": "field",
                        "description": f"Soil moisture is low at {field.moisture_level}% for {field.name}.",
                        "field_id": field.id,
                        "user_id": user_id,
                    }
                    task = TaskService.create_task(data)
                    task.ai_explanation = TaskIntelligenceService.generate_task_explanation(task, context)
                    TaskRepository.update(task, {"ai_explanation": task.ai_explanation})
                    created_tasks.append(task)
                    existing_titles.add(title)

            if (getattr(field, "health_status", "") or "").lower() in ("poor", "alert", "critical"):
                title = f"Inspect {field.name} for stress or disease"
                if title not in existing_titles:
                    data = {
                        "title": title,
                        "priority": "high",
                        "task_type": "inspection",
                        "task_category": "field",
                        "description": f"Field health status is {field.health_status}. Schedule inspection for {field.name}.",
                        "field_id": field.id,
                        "user_id": user_id,
                    }
                    task = TaskService.create_task(data)
                    task.ai_explanation = TaskIntelligenceService.generate_task_explanation(task, context)
                    TaskRepository.update(task, {"ai_explanation": task.ai_explanation})
                    created_tasks.append(task)
                    existing_titles.add(title)

            if getattr(field, "crop", None) is not None and getattr(field.crop, "name", None):
                crop = field.crop
                if getattr(crop, "growth_stage_rel", None) and getattr(crop.growth_stage_rel, "name", None):
                    title = f"Review {crop.name} at {crop.growth_stage_rel.name} stage"
                    if title not in existing_titles:
                        data = {
                            "title": title,
                            "priority": "medium",
                            "task_type": "crop_review",
                            "task_category": "crop",
                            "description": f"Review the crop {crop.name} in field {field.name} at growth stage {crop.growth_stage_rel.name}.",
                            "field_id": field.id,
                            "crop_id": crop.id,
                            "user_id": user_id,
                        }
                        task = TaskService.create_task(data)
                        task.ai_explanation = TaskIntelligenceService.generate_task_explanation(task, context)
                        TaskRepository.update(task, {"ai_explanation": task.ai_explanation})
                        created_tasks.append(task)
                        existing_titles.add(title)

        for task_item in weekly_plan.get("tasks", [])[:10]:
            title = task_item.get("task")
            if not title or title in existing_titles:
                continue
            data = {
                "title": title,
                "priority": "medium",
                "task_type": "general",
                "task_category": "general",
                "description": f"Weekly plan task scheduled for {task_item.get('date')}: {title}.",
                "user_id": user_id,
            }
            task = TaskService.create_task(data)
            task.ai_explanation = TaskIntelligenceService.generate_task_explanation(task, context)
            TaskRepository.update(task, {"ai_explanation": task.ai_explanation})
            created_tasks.append(task)
            existing_titles.add(title)

        return {
            "created": len(created_tasks),
            "task_ids": [task.id for task in created_tasks],
            "seasonal_plan": seasonal_plan,
            "weekly_plan": weekly_plan,
        }
