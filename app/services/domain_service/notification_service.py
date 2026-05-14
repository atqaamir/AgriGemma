import logging

from app.repositories.notification_repository import NotificationRepository
from app.models.notification import Notification

from app.routes.weather import weather
from app.utils.enums_ import NotificationType, Status

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
        """Detect alerts, persist notifications, and return status for coordinator."""
        try:
            from app.services.intelligence_service.context.context_builder import build_notification_context

            context = build_notification_context(user_id)
            alerts = self._detect_from_context(context)
            if not alerts:
                return Status.SUCCESS

            explanation = self._generate_ai_explanation(alerts, context)
            logger.info(
                "AlertService: %d alert(s) for user %s [%s]: %s",
                len(alerts), user_id, tag, explanation[:120],
            )

            for alert_idx, alert_data in enumerate(alerts):
                summary = alert_data.get("message")
                detail = explanation if alert_idx == 0 else alert_data.get("message")
                notification_type = (
                    NotificationType.CRITICAL.value
                    if alert_data.get("level") == "high"
                    else NotificationType.WARNING.value
                )
                self.create_if_not_duplicate(
                    user_id=user_id,
                    title=summary,
                    message=summary,
                    notification_type=notification_type,
                    detail=detail,
                    entity_type=alert_data.get("type"),
                    entity_id=None,
                )

            return Status.SUCCESS
        except Exception as exc:
            logger.error("AlertService.generate_alerts failed: %s", exc)
            return Status.FAILED

    def generate_notifications(self, user_id: int, tag: str = "") -> Status:
        """Backward-compatible wrapper for NotificationAgent flows."""
        return self.generate_alerts(user_id, tag=tag)

    # ── Direct consumer interface (routes, tests) ──────────────────────────

    def generate_alert_for_user(self, user_id: int, context: dict) -> dict:
        """Generate alerts for a specific user based on the provided context."""
        alerts = self._detect_from_context(context)
        explanation = self._generate_ai_explanation(alerts, context) if alerts else "No alerts on your farm right now."

        created_notifications = []
        for alert_data in alerts:
            notification = self.create_if_not_duplicate(
                user_id=user_id,
                title=alert_data.get("message"),
                message=alert_data.get("message"),
                notification_type=(
                    NotificationType.CRITICAL.value
                    if alert_data.get("level") == "high"
                    else NotificationType.WARNING.value
                ),
                detail=explanation,
                entity_type=alert_data.get("type"),
                entity_id=None,
            )
            if notification:
                created_notifications.append(notification)

        return {
            "alerts": alerts,
            "explanation": explanation,
            "created_notifications": [n.id for n in created_notifications],
        }

    def generate_alerts_with_explanation(self, user_id: int) -> dict:
        """
        Returns a dict with the alert list and an AI-generated explanation.
        Useful for test endpoints and notification creation.
        Uses minimal notification context (fields + crops + weather + rules only).
        """
        from app.services.intelligence_service.context.context_builder import build_notification_context
        context     = build_notification_context(user_id)
        alerts      = self._detect_from_context(context)
        explanation = self._generate_ai_explanation(alerts, context) if alerts else "No alerts on your farm right now."
        return {
            "alerts":      alerts,
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
        """Alert detection driven by the rule base — thresholds come from rulebook tables, not magic numbers."""
        from app.services.rule_base_service import RuleBaseService

        alerts = []
        weather  = context.get("weather", {})
        current  = weather.get("current", {})
        temp     = current.get("temp") or current.get("temperature_c") or 0
        rainfall = current.get("rainfall_mm") if current.get("rainfall_mm") is not None else current.get("precipitation_mm", 0)

        crops_data  = context.get("farm", {}).get("active_crops_data", [])
        fields_data = context.get("farm", {}).get("active_fields_data", [])

        for crop in crops_data:
            crop_id  = crop.get("crop_name_id")
            stage_id = crop.get("growth_stage_id")
            moisture = crop.get("moisture_level") or 0
            name     = crop.get("field_name") or crop.get("name", "unnamed field")

            if not crop_id:
                continue

            # ── Soil moisture ───────────────────────────────────────────────
            if moisture < 30:
                m_band, level = "below_30", "high"
            elif moisture > 60:
                m_band, level = "above_60", "medium"
            else:
                m_band = None

            if m_band:
                try:
                    rule = RuleBaseService.get_soil_moisture_action_by_crop_and_range(crop_id, m_band)
                    if rule:
                        alerts.append({
                            "message": f"{rule.reasoning} on {name} ({moisture:.0f}%)",
                            "level": level,
                            "type": "soil",
                            "field_name": name,
                        })
                except Exception as exc:
                    logger.debug("alert detect: soil_moisture — %s", exc)

            # ── Temperature via threshold rulebook ──────────────────────────
            if stage_id and temp > 0:
                try:
                    threshold = RuleBaseService.get_risk_thresholds_by_crop_and_stage(crop_id, stage_id)
                    if threshold:
                        if threshold.temp_heat_critical and temp >= threshold.temp_heat_critical:
                            alerts.append({
                                "message": (
                                    f"Critical heat for {name}: {temp}°C exceeds "
                                    f"{threshold.temp_heat_critical}°C critical threshold"
                                ),
                                "level": "high",
                                "type": "weather",
                                "field_name": name,
                            })
                        elif threshold.temp_heat_caution and temp >= threshold.temp_heat_caution:
                            alerts.append({
                                "message": (
                                    f"Heat caution for {name}: {temp}°C near "
                                    f"{threshold.temp_heat_caution}°C caution threshold"
                                ),
                                "level": "medium",
                                "type": "weather",
                                "field_name": name,
                            })
                except Exception as exc:
                    logger.debug("alert detect: temperature — %s", exc)

            # ── Rainfall via rulebook ───────────────────────────────────────
            if rainfall > 50:
                try:
                    rule = RuleBaseService.get_rainfall_action_by_crop_and_range(crop_id, "above_50")
                    if rule:
                        alerts.append({
                            "message": f"{rule.reasoning} on {name} ({rainfall:.0f}mm)",
                            "level": "medium",
                            "type": "weather",
                            "field_name": name,
                        })
                except Exception as exc:
                    logger.debug("alert detect: rainfall — %s", exc)

        # ── Field health status (direct sensor observation) ─────────────────
        for field in fields_data:
            health = (field.get("health_status") or "").lower()
            name   = field.get("name", "unnamed field")
            if health in ("poor", "alert", "critical", "warning", "risk"):
                alerts.append({
                    "message": f"Crop health '{health}' on {name}: needs immediate attention",
                    "level": "high" if health in ("critical", "risk") else "medium",
                    "type": "crop",
                    "field_name": name,
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
            from app.services.ai_model_service.ai_model_service import fast_complete
            from app.services.intelligence_service.chatbot_service.prompts._prompt_task_intelligence import (
                build_alert_explanation_prompt,
            )
            prompt = build_alert_explanation_prompt(alerts, context)
            return fast_complete(prompt)
        except Exception as exc:
            logger.warning("AlertService: AI explanation failed — %s", exc)
            high = [a for a in alerts if a.get("level") == "high"]
            if high:
                return f"Urgent: {high[0]['message']}. Check your fields as soon as possible."
            return f"{len(alerts)} alert(s) on your farm require attention today."

