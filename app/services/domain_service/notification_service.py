import logging

from app.repositories.notification_repository import NotificationRepository
from app.models.notification import Notification

from app.routes.weather import weather
from app.utils.enums_ import Status

logger = logging.getLogger(__name__)


class NotificationService:

    @staticmethod
    def create(
        user_id: int,
        title: str,
        message: str,
        notification_type: str,
        detail: str = None,
        entity_type: str = None,
        entity_id: int = None,
    ) -> Notification:
        return NotificationRepository.create({
            "user_id": user_id,
            "title": title,
            "message": message,
            "notification_type": notification_type,
            "detail": detail,
            "entity_type": entity_type,
            "entity_id": entity_id,
        })

    @staticmethod
    def create_if_not_duplicate(
        user_id: int,
        title: str,
        message: str,
        notification_type: str,
        detail: str = None,
        entity_type: str = None,
        entity_id: int = None,
        within_minutes: int = 30,
    ) -> Notification | None:
        """Create only if no identical notification exists within the dedup window."""
        if NotificationRepository.recent_duplicate_exists(
            user_id, notification_type, message, within_minutes
        ):
            return None
        return NotificationService.create(
            user_id, title, message, notification_type, detail, entity_type, entity_id
        )

    @staticmethod
    def get_paginated(user_id: int, page: int = 1, per_page: int = 20, notification_type: str = None):
        return NotificationRepository.get_paginated(user_id, page, per_page, notification_type)

    @staticmethod
    def get_by_type(user_id: int, notification_type: str) -> list:
        return NotificationRepository.get_by_type(user_id, notification_type)

    @staticmethod
    def get_unread(user_id: int) -> list:
        return NotificationRepository.get_unread(user_id)

    @staticmethod
    def get_unread_critical(user_id: int) -> list:
        return NotificationRepository.get_unread_critical(user_id)

    @staticmethod
    def get_unread_count(user_id: int) -> int:
        return NotificationRepository.get_unread_count(user_id)

    @staticmethod
    def mark_as_read(notification_id: int):
        return NotificationRepository.mark_as_read(notification_id)

    @staticmethod
    def mark_all_read(user_id: int) -> None:
        NotificationRepository.mark_all_read(user_id)

    @staticmethod
    def delete(notification_id: int):
        return NotificationRepository.delete(notification_id)
    


    """
    Detects farm alerts from live context data and generates AI explanations.

    Two interfaces:
      generate_alerts(user_id, tag)            — called by AlertAgent (coordinator pipeline)
      generate_alerts_with_explanation(user_id) — called by test route / direct consumers
      get_active_alerts(field_id)              — called by ContextAggregationService
    """

    # ── Coordinator-facing (AlertAgent → CoordinatorAgent) ─────────────────

    def generate_alerts(self, user_id: int, tag: str = "") -> Status:
        """Detect alerts and log AI explanation. Returns Status enum for coordinator."""
        try:
            from app.services.intelligence_service.chatbot_service.context_aggregation_service import ContextAggregationService
            context = ContextAggregationService.build_task_context(user_id)
            alerts = self._detect_from_context(context)
            if alerts:
                explanation = self._generate_ai_explanation(alerts, context)
                logger.info(
                    "AlertService: %d alert(s) for user %s [%s]: %s",
                    len(alerts), user_id, tag, explanation[:120],
                )
            return Status.SUCCESS
        except Exception as exc:
            logger.error("AlertService.generate_alerts failed: %s", exc)
            return Status.FAILED

    # ── Direct consumer interface (routes, tests) ──────────────────────────

    def generate_alert_for_user(self, user_id: int, context: dict) -> list:
        """Generate alerts for a specific user based on the provided context

        Context:

            what changed in the weather
            which crop/field is affected
            type of change -> warning / alert / info / critical
            what was changed in plan
            what changed in task/action

            ."""
        
        alert = self._generate_alerts_from_context(context)
        explanation = self._generate_ai_explanation(alert, context)

        """update db with new alert and explanation"""
        """return alert id for reference"""


        

    def generate_alerts_with_explanation(self, user_id: int) -> dict:
        """
        Returns a dict with the alert list and an AI-generated explanation.
        Useful for test endpoints and notification creation.
        """
        from app.services.intelligence_service.chatbot_service.context_aggregation_service import ContextAggregationService
        context = ContextAggregationService.build_task_context(user_id)
        alerts = self._detect_from_context(context)
        explanation = self._generate_ai_explanation(alerts, context) if alerts else "No alerts on your farm right now."
        return {
            "alerts": alerts,
            "explanation": explanation,
            "alert_count": len(alerts),
        }

    def get_active_alerts(self, field_id) -> list:
        """
        Used by ContextAggregationService to collect per-field alerts.
        Returns a static sample — replace with a real DB lookup when available.
        """
        return [
            {
                "message": "Low soil moisture: crops may suffer water stress",
                "level": "high",
                "type": "soil",
            },
            {
                "message": "Crop health warning: needs attention",
                "level": "medium",
                "type": "crop",
            },
        ]

    # ── Private helpers ────────────────────────────────────────────────────

    def _detect_from_context(self, context: dict) -> list:
        """Rule-based alert detection using aggregated farm context."""
        alerts = []
        weather = context.get("weather", {})
        current = weather.get("current", {})
        temp = current.get("temp", 0) or 0
        rainfall = current.get("rainfall_mm", 0) or 0

        for field in context.get("farm", {}).get("active_fields_data", []):
            moisture = field.get("moisture_level") or 0
            health = (field.get("health_status") or "").lower()
            name = field.get("name", "unnamed field")

            if moisture < 25:
                alerts.append({
                    "message": f"Low soil moisture on {name} ({moisture:.0f}%): crops may suffer water stress",
                    "level": "high",
                    "type": "soil",
                    "field_name": name,
                })
            if moisture > 85:
                alerts.append({
                    "message": f"Soil too wet on {name} ({moisture:.0f}%): risk of root damage or fungal disease",
                    "level": "medium",
                    "type": "soil",
                    "field_name": name,
                })
            if health in ("poor", "alert", "critical", "warning", "risk"):
                alerts.append({
                    "message": f"Crop health '{health}' on {name}: needs immediate attention",
                    "level": "high" if health in ("critical", "risk") else "medium",
                    "type": "crop",
                    "field_name": name,
                })

        if temp > 38:
            alerts.append({
                "message": f"Heatwave risk: {temp}°C may damage crops across all fields",
                "level": "high",
                "type": "weather",
                "field_name": "all fields",
            })
        if rainfall > 20:
            alerts.append({
                "message": f"Heavy rain ({rainfall}mm): risk of waterlogging",
                "level": "medium",
                "type": "weather",
                "field_name": "all fields",
            })

        # Deduplicate by message
        seen, unique = set(), []
        for a in alerts:
            if a["message"] not in seen:
                unique.append(a)
                seen.add(a["message"])
        return unique

    @staticmethod
    def _generate_ai_explanation(alerts: list, context: dict) -> str:
        try:
            from app.services.ai_model_service import ai_model_service
            from app.services.intelligence_service.chatbot_service.prompts._prompt_task_intelligence import (
                build_alert_explanation_prompt,
            )
            prompt = build_alert_explanation_prompt(alerts, context)
            return ai_model_service.complete(prompt)
        except Exception as exc:
            logger.warning("AlertService: AI explanation failed — %s", exc)
            high = [a for a in alerts if a.get("level") == "high"]
            if high:
                return f"Urgent: {high[0]['message']}. Check your fields as soon as possible."
            return f"{len(alerts)} alert(s) on your farm require attention today."

