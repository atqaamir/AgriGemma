from app.models.farming_rules import FarmingRule


def apply_runtime_rules(weather: dict, soil: dict, crop: dict, farm: dict | None = None) -> dict:
    """
    Apply rule-based runtime logic for tasks, alerts, and recommendations.
    Uses FarmingRule.matches_runtime(...)
    """
    rules = FarmingRule.query.filter_by(is_active=True).all()

    results = {
        "tasks": [],
        "alerts": [],
        "recommendations": [],
        "plan_adjustments": [],
    }

    for rule in rules:
        if rule.matches_runtime(weather=weather, soil=soil, crop=crop, farm=farm):
            item = {
                "rule_id": rule.id,
                "name": rule.name,
                "message": rule.action_message,
                "priority": rule.priority,
                "type": rule.action_type,
            }

            if rule.action_type == "task":
                results["tasks"].append({
                    "title": rule.action_message,
                    "priority": rule.priority,
                    "source": "rule_engine",
                    "rule_id": rule.id,
                })

            elif rule.action_type == "alert":
                results["alerts"].append({
                    "message": rule.action_message,
                    "level": rule.priority,
                    "type": "rule",
                    "source": "rule_engine",
                    "rule_id": rule.id,
                })

            elif rule.action_type == "recommendation":
                results["recommendations"].append({
                    "message": rule.action_message,
                    "priority": rule.priority,
                    "source": "rule_engine",
                    "rule_id": rule.id,
                })

            elif rule.action_type == "plan_adjustment":
                results["plan_adjustments"].append(item)

    return results


def apply_planning_rules(climate_profile: dict, crop: dict, farm: dict | None = None) -> dict:
    """
    Apply seasonal/planning rules using climate profile data.
    Uses FarmingRule.matches_planning(...)
    """
    rules = FarmingRule.query.filter_by(is_active=True).all()

    results = {
        "recommendations": [],
        "plan_adjustments": [],
    }

    for rule in rules:
        if rule.matches_planning(climate_profile=climate_profile, crop=crop, farm=farm):
            if rule.action_type == "recommendation":
                results["recommendations"].append({
                    "message": rule.action_message,
                    "priority": rule.priority,
                    "source": "rule_engine",
                    "rule_id": rule.id,
                })

            elif rule.action_type == "plan_adjustment":
                results["plan_adjustments"].append({
                    "message": rule.action_message,
                    "priority": rule.priority,
                    "source": "rule_engine",
                    "rule_id": rule.id,
                })

    return results