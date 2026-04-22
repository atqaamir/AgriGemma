from app.rules.rule_engine import rule_engine

class SeasonalPlannerService:
    

    def generate_initial_plan(self, sowing_date, crop_type):
        self.plan = rule_engine.generate_initial_plan(sowing_date, crop_type)
        return self.plan

    def get_active_plan(self, field_id):
        # Implementation for getting active plan for a field
        pass    
    