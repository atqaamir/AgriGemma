from app.rules.rulebooks.range_rules.crop_climate_rulebook import ClimateRulebook
from app.rules.rulebooks.range_rules.soil_climate_rulebook import SoilClimateRulebook
from app.rules.rulebooks.range_rules.water_climate_rulebook import WaterClimateRulebook
from app.rules.rulebooks.range_rules.season_climate_rulebook import SeasonClimateRulebook


class RangeRulesRepository:

    # Crop Climate Rulebook (keys: crop_id, growth_stage_id, soil_type_id)
    @staticmethod
    def get_all_crop_climate() -> list:
        return ClimateRulebook.query.all()

    @staticmethod
    def get_crop_climate_by_crop(crop_id: int) -> list:
        return ClimateRulebook.query.filter_by(crop_id=crop_id).all()

    @staticmethod
    def get_crop_climate_by_crop_and_stage(crop_id: int, growth_stage_id: int) -> list:
        return ClimateRulebook.query.filter_by(crop_id=crop_id, growth_stage_id=growth_stage_id).all()

    @staticmethod
    def get_crop_climate_by_crop_stage_soil(crop_id: int, growth_stage_id: int, soil_type_id: int) -> ClimateRulebook:
        return ClimateRulebook.query.filter_by(
            crop_id=crop_id,
            growth_stage_id=growth_stage_id,
            soil_type_id=soil_type_id,
        ).first()

    # Soil Climate Rulebook (key: crop_id)
    @staticmethod
    def get_all_soil_climate() -> list:
        return SoilClimateRulebook.query.all()

    @staticmethod
    def get_soil_climate_by_crop(crop_id: int) -> SoilClimateRulebook:
        return SoilClimateRulebook.query.filter_by(crop_id=crop_id).first()

    # Water Climate Rulebook (keys: crop_id, growth_stage_id, soil_type_id)
    @staticmethod
    def get_all_water_climate() -> list:
        return WaterClimateRulebook.query.all()

    @staticmethod
    def get_water_climate_by_crop(crop_id: int) -> list:
        return WaterClimateRulebook.query.filter_by(crop_id=crop_id).all()

    @staticmethod
    def get_water_climate_by_crop_and_stage(crop_id: int, growth_stage_id: int) -> list:
        return WaterClimateRulebook.query.filter_by(crop_id=crop_id, growth_stage_id=growth_stage_id).all()

    @staticmethod
    def get_water_climate_by_crop_stage_soil(crop_id: int, growth_stage_id: int, soil_type_id: int) -> WaterClimateRulebook:
        return WaterClimateRulebook.query.filter_by(
            crop_id=crop_id,
            growth_stage_id=growth_stage_id,
            soil_type_id=soil_type_id,
        ).first()

    # Season Climate Rulebook (key: season_id)
    @staticmethod
    def get_all_season_climate() -> list:
        return SeasonClimateRulebook.query.all()

    @staticmethod
    def get_season_climate_by_season(season_id: int) -> SeasonClimateRulebook:
        return SeasonClimateRulebook.query.filter_by(season_id=season_id).first()
