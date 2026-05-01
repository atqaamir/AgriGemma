import logging
import threading

logger = logging.getLogger(__name__)


class TaskEventService:
    """
    Fires background AI intelligence after any task change.
    Runs in a daemon thread so the HTTP response is never blocked.
    Creates critical and recommendation notifications from the result.
    """

    @staticmethod
    def on_task_change(user_id: int, app) -> None:
        thread = threading.Thread(
            target=TaskEventService._run,
            args=(user_id, app),
            daemon=True,
        )
        thread.start()

    @staticmethod
    def _run(user_id: int, app) -> None:
        with app.app_context():
            try:
                from app.agents.coordinator_agent import CoordinatorAgent
                coordinator = CoordinatorAgent()
                coordinator.task_intelligence_agent.invalidate_cache(user_id)
                intelligence = coordinator.generate_task_intelligence(user_id)
                TaskEventService._notify_from_intelligence(user_id, intelligence)
            except Exception as exc:
                logger.error("TaskEventService._run failed (user=%s): %s", user_id, exc)

    @staticmethod
    def _notify_from_intelligence(user_id: int, intelligence: dict) -> None:
        from app.services.domain_service.notification_service import NotificationService

        summary_detail = intelligence.get("summary") or ""

        for action in (intelligence.get("urgent_actions") or []):
            if not action:
                continue
            NotificationService.create_if_not_duplicate(
                user_id=user_id,
                title="Urgent Action Required",
                message=str(action),
                notification_type="critical",
                detail=summary_detail,
            )

        for rec in (intelligence.get("recommendations") or []):
            if not rec:
                continue
            NotificationService.create_if_not_duplicate(
                user_id=user_id,
                title="AI Recommendation",
                message=str(rec),
                notification_type="recommendation",
                detail=summary_detail,
            )
