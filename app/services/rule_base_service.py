from app.rules.vocabulary.mappings import get_id_maps

from app.rules.rule_respositories.vocabulary_repository import VocabularyRepository
from app.rules.rule_respositories.range_rules_repository import RangeRulesRepository
from app.rules.rule_respositories.compatibility_rules_repository import CompatibilityRulesRepository
from app.rules.rule_respositories.action_rules_repository import ActionRulesRepository
from app.rules.rule_respositories.threshold_rules_repository import ThresholdRulesRepository
from app.rules.rule_respositories.event_timelines_rules_repository import EventTimelinesRulesRepository


class RuleBaseService:

    # ------------------------------------------------------------------ #
    #  Vocabulary
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_crop_by_name(name: str):
        return VocabularyRepository.get_crop_by_name(name)

    @staticmethod
    def get_crop_by_id(crop_id: int):
        return VocabularyRepository.get_crop_by_id(crop_id)

    @staticmethod
    def get_all_crop_mapping() -> dict:
        return VocabularyRepository.get_all_crop_mapping()

    @staticmethod
    def get_crop_type_by_name(name: str):
        return VocabularyRepository.get_crop_type_by_name(name)

    @staticmethod
    def get_crop_type_by_id(crop_type_id: int):
        return VocabularyRepository.get_crop_type_by_id(crop_type_id)

    @staticmethod
    def get_all_crop_type_mapping() -> dict:
        return VocabularyRepository.get_all_crop_type_mapping()

    @staticmethod
    def get_stage_by_name(name: str):
        return VocabularyRepository.get_stage_by_name(name)

    @staticmethod
    def get_stage_by_id(stage_id: int):
        return VocabularyRepository.get_stage_by_id(stage_id)

    @staticmethod
    def get_all_stage_mapping() -> dict:
        return VocabularyRepository.get_all_stage_mapping()

    @staticmethod
    def get_season_by_name(name: str):
        return VocabularyRepository.get_season_by_name(name)

    @staticmethod
    def get_season_by_id(season_id: int):
        return VocabularyRepository.get_season_by_id(season_id)

    @staticmethod
    def get_all_season_mapping() -> dict:
        return VocabularyRepository.get_all_season_mapping()

    @staticmethod
    def get_soil_by_name(name: str):
        return VocabularyRepository.get_soil_by_name(name)

    @staticmethod
    def get_soil_by_id(soil_id: int):
        return VocabularyRepository.get_soil_by_id(soil_id)

    @staticmethod
    def get_all_soil_mapping() -> dict:
        return VocabularyRepository.get_all_soil_mapping()

    @staticmethod
    def get_water_source_by_name(name: str):
        return VocabularyRepository.get_water_source_by_name(name)

    @staticmethod
    def get_water_source_by_id(water_source_id: int):
        return VocabularyRepository.get_water_source_by_id(water_source_id)

    @staticmethod
    def get_all_water_source_mapping() -> dict:
        return VocabularyRepository.get_all_water_source_mapping()

    @staticmethod
    def get_all_crop_type_crops() -> dict:
        return VocabularyRepository.get_all_crop_type_crops()

    @staticmethod
    def get_crop_type_by_crop(crop_name: str):
        return VocabularyRepository.get_crop_type_by_crop(crop_name)

    @staticmethod
    def get_all_season_month() -> dict:
        return VocabularyRepository.get_all_season_month()

    @staticmethod
    def get_month_by_season(season_id: int):
        return VocabularyRepository.get_month_by_season(season_id)

    # ------------------------------------------------------------------ #
    #  Range Rules
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_all_crop_climate() -> list:
        return RangeRulesRepository.get_all_crop_climate()

    @staticmethod
    def get_crop_climate_by_crop(crop_id: int) -> list:
        return RangeRulesRepository.get_crop_climate_by_crop(crop_id)

    @staticmethod
    def get_crop_climate_by_crop_and_stage(crop_id: int, growth_stage_id: int) -> list:
        return RangeRulesRepository.get_crop_climate_by_crop_and_stage(crop_id, growth_stage_id)

    @staticmethod
    def get_crop_climate_by_crop_stage_soil(crop_id: int, growth_stage_id: int, soil_type_id: int):
        return RangeRulesRepository.get_crop_climate_by_crop_stage_soil(crop_id, growth_stage_id, soil_type_id)

    @staticmethod
    def get_all_soil_climate() -> list:
        return RangeRulesRepository.get_all_soil_climate()

    @staticmethod
    def get_soil_climate_by_crop(crop_id: int):
        return RangeRulesRepository.get_soil_climate_by_crop(crop_id)

    @staticmethod
    def get_all_water_climate() -> list:
        return RangeRulesRepository.get_all_water_climate()

    @staticmethod
    def get_water_climate_by_crop(crop_id: int) -> list:
        return RangeRulesRepository.get_water_climate_by_crop(crop_id)

    @staticmethod
    def get_water_climate_by_crop_and_stage(crop_id: int, growth_stage_id: int) -> list:
        return RangeRulesRepository.get_water_climate_by_crop_and_stage(crop_id, growth_stage_id)

    @staticmethod
    def get_water_climate_by_crop_stage_soil(crop_id: int, growth_stage_id: int, soil_type_id: int):
        return RangeRulesRepository.get_water_climate_by_crop_stage_soil(crop_id, growth_stage_id, soil_type_id)

    @staticmethod
    def get_all_season_climate() -> list:
        return RangeRulesRepository.get_all_season_climate()

    @staticmethod
    def get_season_climate_by_season(season_id: int):
        return RangeRulesRepository.get_season_climate_by_season(season_id)

    # ------------------------------------------------------------------ #
    #  Compatibility Rules
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_all_climate_compatibility() -> list:
        return CompatibilityRulesRepository.get_all_climate_compatibility()

    @staticmethod
    def get_climate_compatibility_by_crop(crop_id: int) -> list:
        return CompatibilityRulesRepository.get_climate_compatibility_by_crop(crop_id)

    @staticmethod
    def get_climate_compatibility_by_crop_and_stage(crop_id: int, growth_stage_id: int):
        return CompatibilityRulesRepository.get_climate_compatibility_by_crop_and_stage(crop_id, growth_stage_id)

    @staticmethod
    def get_all_soil_climate_compatibility() -> list:
        return CompatibilityRulesRepository.get_all_soil_climate_compatibility()

    @staticmethod
    def get_soil_climate_compatibility_by_crop(crop_id: int) -> list:
        return CompatibilityRulesRepository.get_soil_climate_compatibility_by_crop(crop_id)

    @staticmethod
    def get_soil_climate_compatibility_by_crop_and_stage(crop_id: int, growth_stage_id: int):
        return CompatibilityRulesRepository.get_soil_climate_compatibility_by_crop_and_stage(crop_id, growth_stage_id)

    @staticmethod
    def get_all_crop_soil_compatibility() -> list:
        return CompatibilityRulesRepository.get_all_crop_soil_compatibility()

    @staticmethod
    def get_crop_soil_compatibility_by_crop(crop_id: int) -> list:
        return CompatibilityRulesRepository.get_crop_soil_compatibility_by_crop(crop_id)

    @staticmethod
    def get_crop_soil_compatibility_by_crop_and_soil(crop_id: int, soil_type_id: int):
        return CompatibilityRulesRepository.get_crop_soil_compatibility_by_crop_and_soil(crop_id, soil_type_id)

    @staticmethod
    def get_all_crop_season_compatibility() -> list:
        return CompatibilityRulesRepository.get_all_crop_season_compatibility()

    @staticmethod
    def get_crop_season_compatibility_by_crop(crop_id: int) -> list:
        return CompatibilityRulesRepository.get_crop_season_compatibility_by_crop(crop_id)

    @staticmethod
    def get_crop_season_compatibility_by_crop_and_season(crop_id: int, season_id: int):
        return CompatibilityRulesRepository.get_crop_season_compatibility_by_crop_and_season(crop_id, season_id)

    @staticmethod
    def get_all_water_source_compatibility() -> list:
        return CompatibilityRulesRepository.get_all_water_source_compatibility()

    @staticmethod
    def get_water_source_compatibility_by_crop(crop_id: int) -> list:
        return CompatibilityRulesRepository.get_water_source_compatibility_by_crop(crop_id)

    @staticmethod
    def get_water_source_compatibility_by_crop_and_source(crop_id: int, water_source_id: int):
        return CompatibilityRulesRepository.get_water_source_compatibility_by_crop_and_source(crop_id, water_source_id)

    @staticmethod
    def get_all_crop_type_season_compatibility() -> list:
        return CompatibilityRulesRepository.get_all_crop_type_season_compatibility()

    @staticmethod
    def get_crop_type_season_compatibility_by_type(crop_type_id: int) -> list:
        return CompatibilityRulesRepository.get_crop_type_season_compatibility_by_type(crop_type_id)

    @staticmethod
    def get_crop_type_season_compatibility_by_type_and_season(crop_type_id: int, season_id: int):
        return CompatibilityRulesRepository.get_crop_type_season_compatibility_by_type_and_season(crop_type_id, season_id)

    # ------------------------------------------------------------------ #
    #  Action Rules
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_all_soil_actions() -> list:
        return ActionRulesRepository.get_all_soil_actions()

    @staticmethod
    def get_soil_action_by_crop(crop_id: int) -> list:
        return ActionRulesRepository.get_soil_action_by_crop(crop_id)

    @staticmethod
    def get_soil_action_by_crop_and_soil(crop_id: int, soil_type_id: int):
        return ActionRulesRepository.get_soil_action_by_crop_and_soil(crop_id, soil_type_id)

    @staticmethod
    def get_all_season_actions() -> list:
        return ActionRulesRepository.get_all_season_actions()

    @staticmethod
    def get_season_action_by_crop(crop_id: int) -> list:
        return ActionRulesRepository.get_season_action_by_crop(crop_id)

    @staticmethod
    def get_season_action_by_crop_and_season(crop_id: int, season_id: int):
        return ActionRulesRepository.get_season_action_by_crop_and_season(crop_id, season_id)

    @staticmethod
    def get_all_temperature_actions() -> list:
        return ActionRulesRepository.get_all_temperature_actions()

    @staticmethod
    def get_temperature_action_by_crop(crop_id: int) -> list:
        return ActionRulesRepository.get_temperature_action_by_crop(crop_id)

    @staticmethod
    def get_temperature_action_by_crop_and_range(crop_id: int, growth_stage_id: int, temp_range: str):
        return ActionRulesRepository.get_temperature_action_by_crop_and_range(crop_id, growth_stage_id, temp_range)

    @staticmethod
    def get_all_humidity_actions() -> list:
        return ActionRulesRepository.get_all_humidity_actions()

    @staticmethod
    def get_humidity_action_by_crop(crop_id: int) -> list:
        return ActionRulesRepository.get_humidity_action_by_crop(crop_id)

    @staticmethod
    def get_humidity_action_by_crop_and_range(crop_id: int, growth_stage_id: int, humidity_range: str):
        return ActionRulesRepository.get_humidity_action_by_crop_and_range(crop_id, growth_stage_id, humidity_range)

    @staticmethod
    def get_all_soil_moisture_actions() -> list:
        return ActionRulesRepository.get_all_soil_moisture_actions()

    @staticmethod
    def get_soil_moisture_action_by_crop(crop_id: int) -> list:
        return ActionRulesRepository.get_soil_moisture_action_by_crop(crop_id)

    @staticmethod
    def get_soil_moisture_action_by_crop_and_range(crop_id: int, growth_stage_id: int, moisture_range: str):
        return ActionRulesRepository.get_soil_moisture_action_by_crop_and_range(crop_id, growth_stage_id, moisture_range)

    @staticmethod
    def get_all_ph_actions() -> list:
        return ActionRulesRepository.get_all_ph_actions()

    @staticmethod
    def get_ph_action_by_crop(crop_id: int) -> list:
        return ActionRulesRepository.get_ph_action_by_crop(crop_id)

    @staticmethod
    def get_ph_action_by_crop_and_category(crop_id: int, growth_stage_id: int, ph_category: str):
        return ActionRulesRepository.get_ph_action_by_crop_and_category(crop_id, growth_stage_id, ph_category)

    @staticmethod
    def get_all_sunlight_actions() -> list:
        return ActionRulesRepository.get_all_sunlight_actions()

    @staticmethod
    def get_sunlight_action_by_crop(crop_id: int) -> list:
        return ActionRulesRepository.get_sunlight_action_by_crop(crop_id)

    @staticmethod
    def get_sunlight_action_by_crop_and_range(crop_id: int, growth_stage_id: int, sunlight_range: str):
        return ActionRulesRepository.get_sunlight_action_by_crop_and_range(crop_id, growth_stage_id, sunlight_range)

    @staticmethod
    def get_all_water_source_actions() -> list:
        return ActionRulesRepository.get_all_water_source_actions()

    @staticmethod
    def get_water_source_action_by_crop(crop_id: int) -> list:
        return ActionRulesRepository.get_water_source_action_by_crop(crop_id)

    @staticmethod
    def get_water_source_action_by_crop_and_source(crop_id: int, water_source_id: int):
        return ActionRulesRepository.get_water_source_action_by_crop_and_source(crop_id, water_source_id)

    @staticmethod
    def get_all_rainfall_actions() -> list:
        return ActionRulesRepository.get_all_rainfall_actions()

    @staticmethod
    def get_rainfall_action_by_crop(crop_id: int) -> list:
        return ActionRulesRepository.get_rainfall_action_by_crop(crop_id)

    @staticmethod
    def get_rainfall_action_by_crop_and_range(crop_id: int, growth_stage_id: int, rainfall_range: str):
        return ActionRulesRepository.get_rainfall_action_by_crop_and_range(crop_id, growth_stage_id, rainfall_range)

    # ------------------------------------------------------------------ #
    #  Threshold Rules
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_all_risk_thresholds() -> list:
        return ThresholdRulesRepository.get_all_risk_thresholds()

    @staticmethod
    def get_risk_thresholds_by_crop(crop_id: int) -> list:
        return ThresholdRulesRepository.get_risk_thresholds_by_crop(crop_id)

    @staticmethod
    def get_risk_thresholds_by_crop_and_stage(crop_id: int, growth_stage_id: int):
        return ThresholdRulesRepository.get_risk_thresholds_by_crop_and_stage(crop_id, growth_stage_id)

    @staticmethod
    def get_all_irrigation_frequency() -> list:
        return ThresholdRulesRepository.get_all_irrigation_frequency()

    @staticmethod
    def get_irrigation_frequency_by_crop(crop_id: int) -> list:
        return ThresholdRulesRepository.get_irrigation_frequency_by_crop(crop_id)

    @staticmethod
    def get_irrigation_frequency_by_crop_and_stage(crop_id: int, growth_stage_id: int) -> list:
        return ThresholdRulesRepository.get_irrigation_frequency_by_crop_and_stage(crop_id, growth_stage_id)

    @staticmethod
    def get_irrigation_frequency_with_fallback(crop_id: int, growth_stage_id: int):
        return ThresholdRulesRepository.get_irrigation_frequency_with_fallback(crop_id, growth_stage_id)

    @staticmethod
    def get_all_irrigation_calendar() -> list:
        return ThresholdRulesRepository.get_all_irrigation_calendar()

    @staticmethod
    def get_irrigation_calendar_by_crop(crop_id: int):
        return ThresholdRulesRepository.get_irrigation_calendar_by_crop(crop_id)

    @staticmethod
    def get_all_fertilization_calendar() -> list:
        return ThresholdRulesRepository.get_all_fertilization_calendar()

    @staticmethod
    def get_fertilization_calendar_by_crop(crop_id: int):
        return ThresholdRulesRepository.get_fertilization_calendar_by_crop(crop_id)

    # ------------------------------------------------------------------ #
    #  Event Timelines
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_all_crop_type_timelines() -> list:
        return EventTimelinesRulesRepository.get_all_crop_type_timelines()

    @staticmethod
    def get_timeline_by_crop_type(crop_type_id: int):
        return EventTimelinesRulesRepository.get_timeline_by_crop_type(crop_type_id)

    # ------------------------------------------------------------------ #
    #  Aggregate helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_crop_rules(crop_id: int) -> dict:
        pass

    @staticmethod
    def get_sowing_rules(crop_id: int) -> dict:
        pass

    @staticmethod
    def get_irrigation_rules(crop_id: int) -> dict:
        pass

    @staticmethod
    def get_fertilizer_rules(crop_id: int) -> dict:
        pass

    # ------------------------------------------------------------------ #
    #  Weather Lookups
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_weather_by_region_and_date(region: str, query_date):
        """Return the ClimateProfile row for a given region and date, or None."""
        from app.models.weather import ClimateProfile
        return ClimateProfile.query.filter_by(region=region, date=query_date).first()

    # ------------------------------------------------------------------ #
    #  Planning Helpers
    # ------------------------------------------------------------------ #

    def get_best_season_by_crop_type(self, crop_name):
        return max(self.get_crop_type_season_compatibility_by_type(self.get_crop_type_by_crop(crop_name)), key=lambda r: r.score).season_id

    def get_best_season_by_crop(self, crop_name):
        return max(self.get_crop_season_compatibility_by_crop(self.get_crop_by_name(crop_name).id), key=lambda r: r.score).season_id


rule_base_service = RuleBaseService()
