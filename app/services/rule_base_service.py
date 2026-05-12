# This is the ONLY place that reads crop_rules

class RuleBaseService:

    @staticmethod
    def get_crop_rules(crop: str) -> dict:
        pass

    @staticmethod
    def get_sowing_rules(crop: str) -> dict:
        pass

    @staticmethod
    def get_irrigation_rules(crop: str) -> dict:
        pass

    @staticmethod
    def get_fertilizer_rules(crop: str) -> dict:
        pass


rule_base_service = RuleBaseService()