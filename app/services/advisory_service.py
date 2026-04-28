class AdvisoryService:
    def __init__(self):
        pass


    def build_daily_advisory(self,field_id, context, risk_context, update_result):
        # Analyze the context and risk factors to generate an advisory
        # This is a placeholder implementation and should be replaced with actual logic
        if risk_context.get("disease_risk") == "high":
            return "High disease risk detected. Consider applying fungicides."
        elif risk_context.get("pest_risk") == "high":
            return "High pest risk detected. Consider applying pesticides."
        else:
            return "No immediate risks detected. Continue monitoring."  
        

    def build_plan_change_advisory(self,field_id, context, proposed_revision):
        # Analyze the proposed revision and generate an advisory
        # This is a placeholder implementation and should be replaced with actual logic
        if proposed_revision.get("change_type") == "irrigation":
            return "Proposed change: Adjust irrigation schedule. Ensure soil moisture levels are optimal."
        elif proposed_revision.get("change_type") == "fertilization":
            return "Proposed change: Adjust fertilization plan. Ensure nutrient levels are balanced."
        else:
            return "Proposed change detected. Please review the details and ensure it aligns with best practices."