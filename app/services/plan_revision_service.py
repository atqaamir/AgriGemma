class PlanRevisionService:
    def __init__(self, plan_repository):
        self.plan_repository = plan_repository

    def revise_plan(self, plan_id, new_details):
        plan = self.plan_repository.get_by_id(plan_id)
        if not plan:
            raise ValueError("Plan not found")
        
        # Update the plan details
        for key, value in new_details.items():
            setattr(plan, key, value)
        
        self.plan_repository.save(plan)
        return plan


    def create_proposed_revision(self, field_id, update_result):
        # Logic to create a proposed revision based on the update result
        pass    

    def approve_revision(self, revision_id):

        # Logic to approve a proposed revision
        pass
    def reject_revision(self, revision_id):
        # Logic to reject a proposed revision
        pass