from app.rules.Predictive.rule_engine import RuleEngine

class SeasonalPlannerService:
    
    rule_engine = RuleEngine()

    def generate_initial_plan(self, sowing_date, crop_type):
        self.plan = self.rule_engine.generate_initial_plan(sowing_date, crop_type)
        return self.plan

    def get_active_plan(self, field_id):
        # Implementation for getting active plan for a field
        pass    
    