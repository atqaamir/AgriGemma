class WeeklyPlannerService:
    def __init__(self, context_service):
        self.context_service = context_service

    def generate_weekly_plan(self, field_id):
        # Get field information
        field_info = self.context_service.field_service.get_field_info(field_id)
        
        # Get crop information
        crop_info = self.context_service.crop_service.get_crop_info(field_info['crop_id'])
        
        # Get seasonal plan
        seasonal_plan = self.context_service.seasonal_planner_service.get_seasonal_plan(crop_info['crop_id'])
        
        # Get tasks for the week based on the seasonal plan
        weekly_tasks = self.context_service.task_service.get_weekly_tasks(seasonal_plan['seasonal_plan_id'])
        
        return {
            "field": field_info,
            "crop": crop_info,
            "weekly_tasks": weekly_tasks
        }