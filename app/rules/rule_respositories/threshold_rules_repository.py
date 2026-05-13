from app.rules.rulebooks.threshold_rules.risk_thresholds_rulebook import ThresholdRulebook
from app.rules.rulebooks.threshold_rules.irrigation_frequency_rulebook import IrrigationFrequencyRulebook
from app.rules.rulebooks.threshold_rules.irrigation_calender_rulebook import IrrigationCalenderRulebook


class ThresholdRulesRepository:

    # Risk Thresholds (keys: crop_id, growth_stage_id)
    @staticmethod
    def get_all_risk_thresholds() -> list:
        return ThresholdRulebook.query.all()

    @staticmethod
    def get_risk_thresholds_by_crop(crop_id: int) -> list:
        return ThresholdRulebook.query.filter_by(crop_id=crop_id).all()

    @staticmethod
    def get_risk_thresholds_by_crop_and_stage(crop_id: int, growth_stage_id: int) -> ThresholdRulebook:
        return ThresholdRulebook.query.filter_by(crop_id=crop_id, growth_stage_id=growth_stage_id).first()

    # Irrigation Frequency Rulebook (keys: crop_id, growth_stage_id, soil_type_id)
    @staticmethod
    def get_all_irrigation_frequency() -> list:
        return IrrigationFrequencyRulebook.query.all()

    @staticmethod
    def get_irrigation_frequency_by_crop(crop_id: int) -> list:
        return IrrigationFrequencyRulebook.query.filter_by(crop_id=crop_id).all()

    @staticmethod
    def get_irrigation_frequency_by_crop_and_stage(crop_id: int, growth_stage_id: int) -> list:
        return IrrigationFrequencyRulebook.query.filter_by(crop_id=crop_id, growth_stage_id=growth_stage_id).all()

    @staticmethod
    def get_irrigation_frequency_by_crop_stage_soil(crop_id: int, growth_stage_id: int, soil_type_id: int) -> IrrigationFrequencyRulebook:
        return IrrigationFrequencyRulebook.query.filter_by(
            crop_id=crop_id,
            growth_stage_id=growth_stage_id,
            soil_type_id=soil_type_id,
        ).first()

    # Irrigation Calendar (key: crop_id)
    @staticmethod
    def get_all_irrigation_calendar() -> list:
        return IrrigationCalenderRulebook.query.all()

    @staticmethod
    def get_irrigation_calendar_by_crop(crop_id: int) -> IrrigationCalenderRulebook:
        return IrrigationCalenderRulebook.query.filter_by(crop_id=crop_id).first()
