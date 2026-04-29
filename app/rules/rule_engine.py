# Generate crop rules knowlage base here
# This file contains logic ONLY

from datetime import timedelta
from app.services.rule_base_service import rule_base_service


class RuleEngine:

    @staticmethod
    def evaluate_sowing(rain_mm: float, crop: str) -> dict:
        sowing_rules = rule_base_service.get_sowing_rules(crop)

        threshold = sowing_rules.get("rain_threshold_mm", 15)

        if rain_mm > threshold:
            return {
                "action": "delay_sowing",
                "reason": "heavy_rain",
                "risk": "high"
            }

        return {
            "action": "proceed",
            "risk": "low"
        }

    @staticmethod
    def generate_initial_plan(sowing_date, crop: str) -> dict:
        irrigation_rules = rule_base_service.get_irrigation_rules(crop)
        fertilizer_rules = rule_base_service.get_fertilizer_rules(crop)

        irrigation_days = irrigation_rules.get("days_after_sowing", 7)
        fertilizer_days = fertilizer_rules.get("days_after_sowing", 15)

        return {
            "sowing": sowing_date,
            "first_irrigation": sowing_date + timedelta(days=irrigation_days),
            "fertilizer_application": sowing_date + timedelta(days=fertilizer_days)
        }

    @staticmethod
    def adjust_plan_for_rain(plan: dict, rain_mm: float, crop: str) -> dict:
        sowing_decision = RuleEngine.evaluate_sowing(rain_mm, crop)

        if sowing_decision["action"] == "delay_sowing":
            new_sowing = plan["sowing"] + timedelta(days=4)

            return {
                "old_plan": plan,
                "new_plan": {
                    **plan,
                    "sowing": new_sowing
                },
                "change": "sowing_delayed_due_to_rain"
            }

        return {
            "old_plan": plan,
            "new_plan": plan,
            "change": "no_change"
        }
