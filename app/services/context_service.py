# app/services/context_service.py
from app.services.domain_service.field_service import FieldService
from app.services.domain_service.crop_service import CropService
from app.services.seasonal_planner_service import SeasonalPlannerService
from app.services.weekly_planning_service.weekly_planner_service import WeeklyPlannerService
from app.services.domain_service.task_service import TaskService


class ContextService:
    field = FieldService()
    seasonal_planner = SeasonalPlannerService()
    weekly_planner = WeeklyPlannerService()

    task = TaskService()

    def get_crop_related_tasks_list(self, crop_id):
        return self.task.get_pending_tasks_list_by_crop_id(crop_id)
   
    
    def get_crop_related_tasks(self, crop_id):
        return self.get_pending_tasks_details_by_crop_id(crop_id)
    

    def get_field_related_tasks_list(self, field_id):
        return self.task.get_pending_tasks_list_by_field_id(field_id)
   
    
    def get_field_related_tasks(self, field_id):
        return self.get_pending_tasks_details_by_field_id(field_id)
    
    




