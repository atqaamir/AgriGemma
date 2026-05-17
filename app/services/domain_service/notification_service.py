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
        """
        Tag-driven notification dispatch:
          weather_only   → INFO    — weather shifted but tasks are unaffected; no AI call
          weekly         → WARNING — weather changed the weekly plan; today's tasks fine;
                                     Ollama explains what changed and why
          daily          → ALERT   — weather changed the weekly plan AND today's tasks;
                                     Ollama explains the changes and what to prioritise
          change_summary → CHANGE  — full change report with Ollama summary;
                                     triggers an alert popup when unread
        """
        try:
            from app.services.intelligence_service.context.context_builder import build_notification_context
            context = build_notification_context(user_id)
            weather = context.get("weather", {})

            if tag == "weather_only":
                # INFO — no AI explanation needed
                self.create_if_not_duplicate(
                    user_id=user_id,
                    title="Weather changed, you're all good",
                    message=self._build_short_message("weather_only", weather),
                    notification_type=NotificationType.INFO.value,
                    detail=None,
                )
                print(f"[weather_only notification] created for user={user_id}")

            elif tag == "weekly":
                # WARNING — weekly plan adjusted, today unchanged
                # Ollama explains the weekly shift
                detail = self._generate_plan_change_explanation("weekly", context)
                print(f"[weekly notification] generated detail length={len(detail) if detail else 0}")
                self.create_if_not_duplicate(
                    user_id=user_id,
                    title="Heads up — your week looks a bit different",
                    message=self._build_short_message("weekly", weather),
                    notification_type=NotificationType.WARNING.value,
                    detail=detail,
                )
                print(f"[weekly notification] create_if_not_duplicate returned for user={user_id}")

            elif tag == "daily":
                # ALERT — today's tasks AND weekly plan changed
                # Ollama explains what changed today and what to prioritise
                detail = self._generate_plan_change_explanation("daily", context)
                print(f"[daily notification] generated detail length={len(detail) if detail else 0}")
                self.create_if_not_duplicate(
                    user_id=user_id,
                    title="Your tasks have changed today",
                    message=self._build_short_message("daily", weather),
                    notification_type=NotificationType.ALERT.value,
                    detail=detail,
                )

                print(f"[daily notification] create_if_not_duplicate returned for user={user_id}")

            elif tag == "change_summary":
                # CHANGE — full structured report with Ollama summary; triggers popup alert
                # Always create fresh — each report contains unique weather/task/AI data
                print(f"[change_summary] start for user={user_id}")
                try:
                    task_summaries, plan_summaries = self._collect_change_data(user_id)
                    logger.info("change_summary: collected %d task changes, %d plan changes", 
                               len(task_summaries), len(plan_summaries))
                    print(f"[change_summary] collected task_summaries={len(task_summaries)} plan_summaries={len(plan_summaries)}")
                except Exception as collect_exc:
                    logger.error("change_summary: collect_change_data failed — %s", collect_exc, exc_info=True)
                    print(f"[change_summary] collect_change_data failed: {collect_exc}")
                    task_summaries, plan_summaries = [], []
                
                try:
                    detail = self._build_change_summary_detail(task_summaries, plan_summaries, context)
                    print(f"[change_summary] built detail (len={len(detail) if detail else 0})")
                except Exception as detail_exc:
                    logger.error("change_summary: detail build failed — %s", detail_exc, exc_info=True)
                    print(f"[change_summary] detail build failed: {detail_exc}")
                    detail = None
                
                title = self._build_change_summary_title(task_summaries, plan_summaries)
                message = self._build_change_summary_message(task_summaries, plan_summaries)
                
                try:
                    notification = self.create(
                        user_id=user_id,
                        title=title,
                        message=message,
                        notification_type=NotificationType.CHANGE.value,
                        detail=detail,
                    )
                    print(f"[change_summary] create returned: {getattr(notification, 'id', notification)}")
                    logger.info("change_summary: CHANGE notification created for user %d", user_id)
                except Exception as create_exc:
                    logger.error("change_summary: create notification failed — %s", create_exc, exc_info=True)
                    print(f"[change_summary] create failed: {create_exc}")
                    return Status.FAILED

            return Status.SUCCESS
        except Exception as exc:
            logger.error("NotificationService.generate_notifications failed (tag=%s): %s", tag, exc)
            return Status.FAILED

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
    def _collect_change_data(user_id: int) -> tuple:
        """Fetch changed tasks and weekly plan adjustments for the current user."""
        import json

        # ── Tasks with recorded changes ───────────────────────────────────
        task_summaries = []
        try:
            from app.models.task import Task
            from sqlalchemy.orm import joinedload
            tasks = (
                Task.query
                .options(joinedload(Task.field))
                .filter_by(user_id=user_id, completed=False)
                .all()
            )
            for task in tasks:
                if not task.task_changes:
                    continue
                try:
                    changes = json.loads(task.task_changes) if isinstance(task.task_changes, str) else task.task_changes
                except Exception:
                    continue
                if not changes:
                    continue
                lines = []
                for ch in changes:
                    ct = ch.get("change_type", "")
                    ov = ch.get("original_value")
                    nv = ch.get("new_value")
                    if ct == "priority":
                        lines.append(f"priority {ov} → {nv}")
                    elif ct == "due_date":
                        lines.append(f"due date moved from {ov} to {nv}")
                    elif ct == "is_active":
                        lines.append("deactivated" if not nv else "reactivated")
                if lines:
                    task_summaries.append({
                        "title": task.title,
                        "field": task.field.name if task.field else None,
                        "changes": lines,
                    })
        except Exception as exc:
            logger.warning("change_summary: task fetch failed — %s", exc)

        # ── Weekly plan adjustments ───────────────────────────────────────
        plan_summaries = []
        try:
            from app.models.weekly_plan import WeeklyPlan
            plan = WeeklyPlan.query.filter_by(user_id=user_id, currently_active=True).first()
            if plan and plan.entries:
                for entry in plan.entries:
                    try:
                        adjustments = (
                            json.loads(entry.climate_adjustments)
                            if isinstance(entry.climate_adjustments, str)
                            else (entry.climate_adjustments or [])
                        )
                    except Exception:
                        adjustments = []
                    if adjustments:
                        plan_summaries.append({
                            "crop_id": entry.crop_id,
                            "adjustments": [
                                {
                                    "factor":     adj.get("factor", "weather"),
                                    "reasoning":  adj.get("reasoning", ""),
                                    "adjustment": adj.get("adjustment", ""),
                                }
                                for adj in adjustments
                            ],
                        })
        except Exception as exc:
            logger.warning("change_summary: weekly plan fetch failed — %s", exc)

        return task_summaries, plan_summaries

    @staticmethod
    def _build_change_summary_title(task_summaries: list, plan_summaries: list) -> str:
        """Popup headline — picks the right title based on what actually changed."""
        has_tasks = bool(task_summaries)
        has_plan  = bool(plan_summaries)
        if has_tasks and has_plan:
            return "Your tasks and weekly plan have been changed"
        if has_tasks:
            return "Today's tasks have been changed"
        if has_plan:
            return "Your weekly plan has been changed"
        return "Your plan has been updated"

    @staticmethod
    def _build_change_summary_message(task_summaries: list, plan_summaries: list) -> str:
        """Short subtitle shown under the popup title — one concise line."""
        task_count = len(task_summaries)
        plan_count = len(plan_summaries)

        if task_count and plan_count:
            return (
                f"{task_count} task{'s' if task_count != 1 else ''} and your weekly plan "
                "have been adjusted for today's conditions."
            )
        if task_count:
            return (
                f"{task_count} task{'s' if task_count != 1 else ''} "
                "adjusted due to today's conditions."
            )
        if plan_count:
            return (
                f"Your week has been adjusted across "
                f"{plan_count} crop entr{'ies' if plan_count != 1 else 'y'}."
            )
        return "Your farm plan has been reviewed based on current conditions."

    @staticmethod
    def _build_change_summary_detail(task_summaries: list, plan_summaries: list, context: dict) -> str:
        """
        Builds the full report once at notification creation time.
        Saved to notification.detail in DB — never regenerated on 'View details'.
        Includes AI task intelligence overview + change breakdown.
        """
        from datetime import date as _date

        def _to_float(val):
            try:
                return float(val) if val is not None else None
            except (TypeError, ValueError):
                return None

        farmer    = context.get("farmer_name", "Farmer")
        current   = context.get("weather", {}).get("current", {})
        temp      = _to_float(current.get("temp") or current.get("temperature_c"))
        condition = (current.get("condition") or "").capitalize()
        rainfall  = _to_float(current.get("rainfall_mm") or current.get("precipitation_mm")) or 0.0

        # ── Build text blocks for the AI prompt ──────────────────────────
        tasks_block = "\n".join(
            f"- {t['title']}{' (' + t['field'] + ')' if t.get('field') else ''}: {', '.join(t['changes'])}"
            for t in task_summaries
        ) or "No individual task changes recorded."

        plan_block = "\n".join(
            f"- [{adj['factor']}] {adj['reasoning']} → {adj['adjustment']}"
            for p in plan_summaries for adj in p["adjustments"]
        ) or "No weekly plan adjustments recorded."

        # ── AI summary (single Ollama call) ───────────────────────────────
        ai_summary = ""
        try:
            from app.services.ai_model_service.ai_model_service import fast_complete
            prompt = (
                f"You are a farm advisor. Write 2-3 sentences summarising what changed today for {farmer} "
                f"due to weather ({f'{temp:.0f}°C' if temp is not None else 'N/A'}, {condition}, {rainfall:.0f}mm). "
                f"Tasks: {tasks_block}\n"
                f"Plan: {plan_block}\n"
                f"Be direct and friendly. No bullet points."
            )
            ai_summary = fast_complete(prompt)
        except Exception as exc:
            logger.warning("change_summary: AI summary failed — %s", exc)

        # ── Return structured JSON — frontend renders as a report card ────
        import json
        weather_ctx = context.get("weather", {})
        report = {
            "date":    str(_date.today()),
            "weather": {
                "temp":         temp,
                "condition":    condition,
                "rainfall_mm":  rainfall,
                "heatwave":     weather_ctx.get("heatwave_risk", False),
                "rain_expected": weather_ctx.get("rain_expected", False),
            },
            "tasks":      task_summaries,
            "plan":       [adj for p in plan_summaries for adj in p["adjustments"]],
            "ai_summary": ai_summary,
        }
        return json.dumps(report, ensure_ascii=False)

    @staticmethod
    def _build_short_message(tag: str, weather: dict) -> str:
        """Build a dynamic one-liner from live weather data for the dropdown message."""
        def _to_float(val):
            try:
                return float(val) if val is not None else None
            except (TypeError, ValueError):
                return None

        current   = weather.get("current", {})
        forecast  = weather.get("forecast", [])
        temp      = _to_float(current.get("temp") or current.get("temperature_c"))
        condition = (current.get("condition") or "").capitalize()
        rainfall  = _to_float(current.get("rainfall_mm") or current.get("precipitation_mm")) or 0.0
        humidity  = _to_float(current.get("humidity"))
        wind      = _to_float(current.get("wind_kph"))
        heatwave  = weather.get("heatwave_risk", False)
        rain_exp  = weather.get("rain_expected", False)

        # Summarise the next few forecast days
        upcoming = []
        for day in forecast[:3]:
            day_condition = (day.get("condition") or "").lower()
            rain_chance   = day.get("rain_chance") or 0
            max_t         = day.get("max_temp_c")
            if rain_chance >= 60 or "rain" in day_condition:
                upcoming.append("rain")
            elif max_t and max_t >= 38:
                upcoming.append("heat")
            elif "cloud" in day_condition:
                upcoming.append("cloudy")

        # ── weather_only ──────────────────────────────────────────────────────
        if tag == "weather_only":
            parts = []
            if temp is not None:
                parts.append(f"{temp:.0f}°C" if isinstance(temp, float) else f"{temp}°C")
            if condition and condition.lower() not in ("unknown", ""):
                parts.append(condition.lower())
            if rainfall and rainfall > 0:
                parts.append(f"{rainfall:.0f}mm of rain")
            if humidity:
                parts.append(f"{humidity:.0f}% humidity")
            if wind:
                parts.append(f"winds at {wind:.0f} kph")

            weather_desc = ", ".join(parts) if parts else "some weather changes"

            if heatwave:
                return f"It's hot out there ({weather_desc}) but nothing that changes your tasks today — stay hydrated."
            if rainfall and rainfall > 10:
                return f"Fairly wet today ({weather_desc}), but your tasks aren't affected. Carry on as planned."
            return f"Weather's at {weather_desc} — nothing that affects your tasks today. You're good to go."

        # ── weekly ────────────────────────────────────────────────────────────
        if tag == "weekly":
            drivers = []
            if heatwave:
                drivers.append("a heatwave coming")
            if rain_exp or upcoming.count("rain") >= 2:
                drivers.append("rain expected over the next few days")
            if upcoming.count("heat") >= 2:
                drivers.append("high temperatures expected mid-week")
            if not drivers:
                if temp is not None:
                    drivers.append(f"current conditions ({temp}°C, {condition.lower()})")
                else:
                    drivers.append("shifting weather patterns")

            driver_str = " and ".join(drivers)
            return (
                f"With {driver_str}, we've shifted a few things around in your week. "
                "Today's still fine — it's the next few days that look a little different."
            )

        # ── daily ─────────────────────────────────────────────────────────────
        if tag == "daily":
            if heatwave and temp is not None:
                return (
                    f"It's {temp:.0f}°C and a heatwave risk today — we've updated your tasks "
                    "to keep things manageable in the heat. Check what's changed before you start."
                )
            if rainfall and rainfall > 15:
                return (
                    f"{rainfall:.0f}mm of rain today has shifted some of your tasks around. "
                    "Take a look at the updated list before heading out."
                )
            if rain_exp:
                return (
                    f"Rain's on the way today ({condition.lower() if condition else 'wet conditions'}) "
                    "so we've adjusted your tasks accordingly. Worth a quick check before you start."
                )
            if wind and wind > 40:
                return (
                    f"Strong winds ({wind:.0f} kph) today have changed a few tasks. "
                    "Check your updated list before heading out."
                )
            if temp is not None:
                return (
                    f"Today's weather ({temp:.0f}°C, {condition.lower() if condition else 'current conditions'}) "
                    "has caused some task changes. Take a quick look before you head out."
                )
            return (
                "Today's conditions have caused some changes to your tasks and weekly plan. "
                "Take a quick look before you head out."
            )

        return "Your plan has been updated based on current weather conditions."

    @staticmethod
    def _generate_plan_change_explanation(tag: str, context: dict) -> str:
        """AI reasoning for weekly/daily plan-change notifications via Ollama."""
        try:
            from app.services.ai_model_service.ai_model_service import fast_complete

            farmer   = context.get("farmer_name", "Farmer")
            current  = context.get("weather", {}).get("current", {})
            temp     = current.get("temp") or current.get("temperature_c", "unknown")
            rainfall = current.get("rainfall_mm") or current.get("precipitation_mm", 0)
            crops    = context.get("farm", {}).get("active_crops_data", [])
            fields   = ", ".join(
                c.get("field_name") or c.get("name", "") for c in crops[:3] if c.get("field_name") or c.get("name")
            ) or "the active fields"

            if tag == "weekly":
                prompt = (
                    f"You're a friendly farming assistant talking directly to {farmer}. "
                    f"The weather today is {temp}°C with {rainfall:.0f}mm of rainfall, and it's caused some changes to the weekly farm plan for {fields}. "
                    f"Write 2-3 casual, friendly sentences explaining why the week ahead looks a bit different and what to roughly expect over the next few days. "
                    f"Keep it warm and reassuring — today is still fine, it's just the coming days that need a small adjustment. "
                    f"Don't use bullet points. Write like you're texting a friend who farms."
                )
            else:  # daily
                prompt = (
                    f"You're a friendly farming assistant talking directly to {farmer}. "
                    f"The weather today is {temp}°C with {rainfall:.0f}mm of rainfall, and it's caused changes to both today's tasks and the weekly plan for {fields}. "
                    f"Write 2-3 casual, friendly sentences explaining what changed today because of the weather and what {farmer} should focus on first. "
                    f"Be direct but warm — like a knowledgeable friend giving a quick heads-up. "
                    f"Don't use bullet points. Write like you're texting a friend who farms."
                )

            return fast_complete(prompt)
        except Exception as exc:
            logger.warning("NotificationService: plan change AI explanation failed — %s", exc)
            if tag == "weekly":
                return (
                    "The weather's shifted a bit, so we've tweaked your plan for the next few days. "
                    "Nothing major — today is still on track, just expect a few small changes coming up."
                )
            return (
                "The weather today means a few of your tasks look a bit different. "
                "Take a quick look at your updated list and tackle the most time-sensitive ones first."
            )

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

