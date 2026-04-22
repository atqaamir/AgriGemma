# This is the ONLY place that reads crop_rules

from app.rules.crop_rules import CROP_RULES


class RuleBaseService:

    @staticmethod
    def get_crop_rules(crop: str) -> dict:
        return CROP_RULES.get(crop, {})

    @staticmethod
    def get_sowing_rules(crop: str) -> dict:
        rules = CROP_RULES.get(crop, {})
        return rules.get("sowing", {})

    @staticmethod
    def get_irrigation_rules(crop: str) -> dict:
        rules = CROP_RULES.get(crop, {})
        return rules.get("irrigation", {})

    @staticmethod
    def get_fertilizer_rules(crop: str) -> dict:
        rules = CROP_RULES.get(crop, {})
        return rules.get("fertilizer", {})


rule_base_service = RuleBaseService()