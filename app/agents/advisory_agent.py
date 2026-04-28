from app.services.advisory_service import AdvisoryService as advisory_service


class AdvisoryAgent:
    @staticmethod
    def build_daily_advisory(field_id: str, context: dict, risk_context: dict, update_result: dict) -> dict:
        return advisory_service.build_daily_advisory(
            field_id=field_id,
            context=context,
            risk_context=risk_context,
            update_result=update_result,
        )

    @staticmethod
    def build_plan_change_advisory(field_id: str, context: dict, proposed_revision: dict) -> dict:
        return advisory_service.build_plan_change_advisory(
            field_id=field_id,
            context=context,
            proposed_revision=proposed_revision,
        )