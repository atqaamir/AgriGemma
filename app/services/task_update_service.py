"""Task update service — applies climate-driven changes to today's tasks.

Called during the IMPACT_TASKS branch of the daily update workflow.
"""

import json
import logging
from datetime import date, timedelta, datetime

from app.repositories.task_repository import TaskRepository
from app.repositories.weekly_plan_repository import WeeklyPlanRepository
from app.repositories.weather_repository import WeatherRepository
from app.repositories.forecast_repository import ForecastRepository
from app.services.domain_service.user_service import UserService
from app.rules.rule_engine.rule_engine import RuleEngine
from app.services.rule_base_service import rule_base_service

logger = logging.getLogger(__name__)

PRIORITY_ORDER = ["low", "medium", "high", "critical"]

# Band-direction key → task_type → change descriptor
# Used when no crop_id is available (general / field tasks).
BAND_ACTIONS_GENERAL = {
    "temperature_up": {
        "irrigation": {"change": "priority", "direction": "up"},
        "spraying":   {"change": "delay",    "days": 2},
    },
    "temperature_down": {
        "planting":   {"change": "delay", "days": 4},
        "irrigation": {"change": "delay", "days": 2},
    },
    "rainfall_up": {
        "irrigation":  {"change": "is_active", "value": False},
        "fertilizing": {"change": "delay", "days": 2},
        "spraying":    {"change": "delay", "days": 2},
    },
    "rainfall_down": {
        "irrigation": {"change": "priority", "direction": "up"},
        "planting":   {"change": "delay",    "days": 2},
    },
    "humidity_up": {
        "spraying":   {"change": "delay", "days": 1},
        "harvesting": {"change": "delay", "days": 2},
    },
    "humidity_down": {
        "irrigation": {"change": "priority", "direction": "up"},
    },
    "sunlight_up": {
        "irrigation": {"change": "priority", "direction": "up"},
    },
    "sunlight_down": {
        "planting": {"change": "delay", "days": 2},
    },
}

# task_type → rule-engine action_type
TASK_TO_ACTION_TYPE = {
    "irrigation":  "irrigation",
    "planting":    "sowing",
    "harvesting":  "harvesting",
    "fertilizing": "fertilization",
    "spraying":    "spraying",
}

RULE_LOOKUPS = [
    ("temperature", "avg_temperature_c",
     lambda c, g, b: rule_base_service.get_temperature_action_by_crop_and_range(c, g, b)),
    ("humidity",    "humidity",
     lambda c, g, b: rule_base_service.get_humidity_action_by_crop_and_range(c, g, b)),
    ("sunlight",    "sunlight_hours",
     lambda c, g, b: rule_base_service.get_sunlight_action_by_crop_and_range(c, g, b)),
    ("rainfall",    "rainfall_mm",
     lambda c, g, b: rule_base_service.get_rainfall_action_by_crop_and_range(c, g, b)),
]


def _priority_shift(priority: str, direction: str) -> str:
    idx = PRIORITY_ORDER.index(priority) if priority in PRIORITY_ORDER else 1
    if direction == "up":
        return PRIORITY_ORDER[min(idx + 1, len(PRIORITY_ORDER) - 1)]
    return PRIORITY_ORDER[max(idx - 1, 0)]


def _as_datetime(d: date) -> datetime:
    return datetime(d.year, d.month, d.day)


def _detect_band_changes(user_location: str, as_of_date: date) -> list:
    """Return band-direction keys that changed on as_of_date, e.g. ['rainfall_down', 'temperature_up']."""
    baseline_records = WeatherRepository.get_by_region_and_date_range(
        user_location, as_of_date, as_of_date
    )
    forecast_records = ForecastRepository.get_by_region_and_date_range(
        user_location, as_of_date, as_of_date
    )
    if not baseline_records or not forecast_records:
        return []

    baseline = baseline_records[0]
    forecast = forecast_records[0]
    changes = []

    for factor, attr in [
        ("temperature", "avg_temperature_c"),
        ("humidity",    "humidity"),
        ("rainfall",    "rainfall_mm"),
        ("sunlight",    "sunlight_hours"),
    ]:
        b_val = getattr(baseline, attr, None)
        f_val = getattr(forecast, attr, None)
        if b_val is None or f_val is None:
            continue
        b_band = RuleEngine.classify_value_bands(factor, b_val)
        f_band = RuleEngine.classify_value_bands(factor, f_val)
        if b_band == f_band:
            continue
        direction = "up" if f_val > b_val else "down"
        changes.append(f"{factor}_{direction}")

    return changes


def _get_growth_stage_by_crop(user_id: int, crop_id: int):
    """Return growth_stage_id for a crop from the user's active weekly plan entries."""
    plan = WeeklyPlanRepository.get_active_by_user_id(user_id)
    if not plan:
        return None
    for entry in plan.entries:
        if entry.crop_id == crop_id:
            return entry.growth_stage_id
    return None


def _apply_rule_engine_action(action: dict, task, as_of_date: date, changes: list) -> bool:
    """Apply one rule-engine action dict to a task. Returns True if modified."""
    action_type = action.get("action_type", "")
    adjustment  = action.get("adjustment", "")
    adj_type    = action.get("adjustment_type", "")
    modified    = False

    if action_type == "irrigation":
        if adjustment == "increase days":
            new_p = _priority_shift(task.priority, "up")
            if new_p != task.priority:
                changes.append({"change_type": "priority", "original_value": task.priority, "new_value": new_p})
                task.priority = new_p
                modified = True
        elif adjustment == "decrease days":
            if task.is_active:
                changes.append({"change_type": "is_active", "original_value": True, "new_value": False})
                task.is_active = False
                modified = True

    elif action_type in ("sowing", "harvesting") and adjustment == "delay":
        days = 4 if adj_type == "minimal" else 7
        if task.due_date:
            new_due = task.due_date + timedelta(days=days)
            changes.append({"change_type": "due_date", "original_value": task.due_date.isoformat(), "new_value": new_due.isoformat()})
            task.due_date = new_due
            modified = True

    elif action_type == "fertilization":
        direction = "up" if adjustment == "increase quantity" else "down"
        new_p = _priority_shift(task.priority, direction)
        if new_p != task.priority:
            changes.append({"change_type": "priority", "original_value": task.priority, "new_value": new_p})
            task.priority = new_p
            modified = True

    elif action_type == "spraying":
        if task.due_date:
            new_due = task.due_date + timedelta(days=2)
            changes.append({"change_type": "due_date", "original_value": task.due_date.isoformat(), "new_value": new_due.isoformat()})
            task.due_date = new_due
            modified = True

    elif action_type == "avoid":
        if task.is_active:
            changes.append({"change_type": "is_active", "original_value": True, "new_value": False})
            task.is_active = False
            modified = True

    return modified


def _apply_general_rules(task, band_changes: list, changes: list, as_of_date: date) -> bool:
    """Apply BAND_ACTIONS_GENERAL based on which weather bands changed."""
    modified = False

    # Snapshot originals before applying any changes so we record one consolidated entry
    original_priority = task.priority
    original_due_date = task.due_date
    original_is_active = task.is_active

    for band_key in band_changes:
        action = BAND_ACTIONS_GENERAL.get(band_key, {}).get(task.task_type)
        if not action:
            continue

        change_type = action["change"]

        if change_type == "priority":
            new_p = _priority_shift(task.priority, action["direction"])
            if new_p != task.priority:
                task.priority = new_p
                modified = True

        elif change_type == "delay":
            if task.due_date:
                task.due_date = task.due_date + timedelta(days=action.get("days", 2))
                modified = True

        elif change_type == "is_active":
            new_val = action["value"]
            if task.is_active != new_val:
                task.is_active = new_val
                modified = True

    # Record one consolidated entry per field that actually changed
    if task.priority != original_priority:
        changes.append({"change_type": "priority", "original_value": original_priority, "new_value": task.priority})
    if task.due_date != original_due_date:
        changes.append({"change_type": "due_date", "original_value": original_due_date.isoformat() if original_due_date else None, "new_value": task.due_date.isoformat() if task.due_date else None})
    if task.is_active != original_is_active:
        changes.append({"change_type": "is_active", "original_value": original_is_active, "new_value": task.is_active})

    return modified


def _apply_crop_rules(task, user_id: int, as_of_date: date, changes: list, band_changes: list) -> bool:
    """Look up rule-engine actions for this crop + growth_stage + forecast band and apply."""
    growth_stage_id = _get_growth_stage_by_crop(user_id, task.crop_id)
    user_location   = UserService.get_user_location(user_id)
    forecast        = RuleEngine.get_forecast_by_region_and_date(user_location, as_of_date) if user_location else None
    if not forecast:
        return False

    action_type_key = TASK_TO_ACTION_TYPE.get(task.task_type)
    if not action_type_key:
        return False

    modified = False
    for factor, weather_attr, lookup_fn in RULE_LOOKUPS:
        if not any(c.startswith(factor) for c in band_changes):
            continue

        value = forecast.get(weather_attr)
        if value is None:
            continue

        band        = RuleEngine.classify_value_bands(factor, value)
        action_rule = lookup_fn(task.crop_id, growth_stage_id, band)
        if not action_rule:
            continue

        raw = action_rule.actions
        actions = json.loads(raw) if isinstance(raw, str) else (raw or [])
        for action in actions:
            if action.get("action_type") == action_type_key:
                if _apply_rule_engine_action(action, task, as_of_date, changes):
                    modified = True

    return modified


class TaskUpdateService:

    @staticmethod
    def update_tasks(user_id: int, as_of_date: date = None) -> dict:
        """Apply climate-driven changes to today's pending tasks.

        Returns a summary dict with counts of modified tasks.
        """
        if as_of_date is None:
            as_of_date = date.today()

        user_location = UserService.get_user_location(user_id)
        if not user_location:
            logger.warning("TaskUpdateService: no location for user %s", user_id)
            return {"modified": 0}

        band_changes = _detect_band_changes(user_location, as_of_date)
        if not band_changes:
            logger.info("TaskUpdateService: no band changes for user %s on %s", user_id, as_of_date)
            return {"modified": 0}

        logger.info("TaskUpdateService: band changes for user %s: %s", user_id, band_changes)

        all_tasks = TaskRepository.get_by_user_id(user_id)
        pending = [
            t for t in all_tasks
            if not t.completed
            and t.is_active
            and (t.due_date is None or t.due_date >= as_of_date)
        ]

        modified_count = 0
        directly_modified_ids = set()

        for task in pending:
            task_changes_list = []

            if task.crop_id is not None and task.task_category == "crop":
                modified = _apply_crop_rules(task, user_id, as_of_date, task_changes_list, band_changes)
            else:
                modified = _apply_general_rules(task, band_changes, task_changes_list, as_of_date)

            if modified:
                TaskRepository.update(task, {
                    "priority":     task.priority,
                    "due_date":     task.due_date,
                    "is_active":    task.is_active,
                    "task_changes": json.dumps(task_changes_list),
                    "created_at":   _as_datetime(as_of_date),
                })
                directly_modified_ids.add(task.id)
                modified_count += 1

        # Lower priority by one level for all unaffected tasks when any change occurred
        if directly_modified_ids:
            for task in pending:
                if task.id in directly_modified_ids:
                    continue
                if task.priority == "low":
                    continue
                new_p = _priority_shift(task.priority, "down")
                TaskRepository.update(task, {
                    "priority":     new_p,
                    "task_changes": json.dumps([{"change_type": "priority", "original_value": task.priority, "new_value": new_p}]),
                    "created_at":   _as_datetime(as_of_date),
                })
                modified_count += 1

        return {"modified": modified_count}
