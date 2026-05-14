import logging

from app.services.intelligence_service.chatbot_service.context_aggregation_service import ContextAggregationService
from app.services.task_intelligence_service import TaskIntelligenceService

logger = logging.getLogger(__name__)


class TaskIntelligenceAgent:
    """
    Thin orchestration agent responsible for the task intelligence pipeline.
    Delegates context aggregation to ContextAggregationService and AI
    generation to TaskIntelligenceService.  Never contains business logic.



    Tasks + Critical tasks overview
    """

    def __init__(self) -> None:
        # Agents are thin — no state beyond the services they coordinate
        pass

    def generate(self, user_id: int) -> dict:
        context = self._aggregate_context(user_id)
        return TaskIntelligenceService.generate_intelligence(context, user_id)

    def invalidate_cache(self, user_id: int) -> None:
        """Expose cache invalidation so the coordinator can refresh after task changes."""
        TaskIntelligenceService.invalidate_cache(user_id)

    # ── Private ───────────────────────────────────────────────────────────────

    def _aggregate_context(self, user_id: int) -> dict:
        try:
            return ContextAggregationService.build_task_context(user_id)
        except Exception as exc:
            logger.error(
                "TaskIntelligenceAgent: context aggregation failed for user %s — %s",
                user_id,
                exc,
            )
            return {}
