from app.agents.context_agent import ContextAgent
from app.agents.risk_agent import RiskAgent
from app.agents.planning_agent import PlanningAgent
from app.agents.advisory_agent import AdvisoryAgent


class CoordinatorAgent:
    @staticmethod
    def handle_daily_system_update(field_id: str) -> dict:
        context = ContextAgent.get_context(field_id)
        risk_context = RiskAgent.get_risk_context(field_id)

        update_result = PlanningAgent.evaluate_daily_update(
            field_id=field_id,
            context=context,
            risk_context=risk_context,
        )

        response = {
            "field_id": field_id,
            "context": context,
            "risk_context": risk_context,
            "update_result": update_result,
        }

        if update_result.get("needs_plan_revision"):
            proposed_revision = PlanningAgent.create_proposed_revision(
                field_id=field_id,
                update_result=update_result,
            )
            advisory = AdvisoryAgent.build_plan_change_advisory(
                field_id=field_id,
                context=context,
                proposed_revision=proposed_revision,
            )
            response["proposed_revision"] = proposed_revision
            response["advisory"] = advisory
        else:
            advisory = AdvisoryAgent.build_daily_advisory(
                field_id=field_id,
                context=context,
                risk_context=risk_context,
                update_result=update_result,
            )
            response["advisory"] = advisory

        return response

    @staticmethod
    def handle_weekly_planning(field_id: str) -> dict:
        context = ContextAgent.get_context(field_id)
        weekly_plan = PlanningAgent.generate_weekly_plan(field_id, context)
        daily_tasks = PlanningAgent.generate_daily_tasks(field_id, weekly_plan)

        return {
            "field_id": field_id,
            "context": context,
            "weekly_plan": weekly_plan,
            "daily_tasks": daily_tasks,
        }

    @staticmethod
    def handle_chat(field_id: str, user_message: str) -> dict:
        context = ContextAgent.get_context(field_id)
        risk_context = RiskAgent.get_risk_context(field_id)

        return {
            "field_id": field_id,
            "user_message": user_message,
            "context": context,
            "risk_context": risk_context,
        }