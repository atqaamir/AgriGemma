from app.rules.rulebooks.compatibility_rules.climate_compatibility_rulebook import ClimateCompatibilityRulebook
from app.rules.rulebooks.compatibility_rules.soil_climate_compatibility_rulebook import SoilClimateCompatibilityRulebook
from app.rules.rulebooks.compatibility_rules.crop_soil_compatibility_rulebook import CropSoilCompatibilityRulebook
from app.rules.rulebooks.compatibility_rules.crop_season_compatibility_rulebook import CropSeasonCompatibilityRulebook
from app.rules.rulebooks.compatibility_rules.water_source_compatibility_rulebook import WaterSourceCompatibilityRulebook
from app.rules.rulebooks.compatibility_rules.irrigation_frequency_compatibility_rulebook import IrrigationFrequencyCompatibilityRulebook
from app.rules.rulebooks.compatibility_rules.crop_type_season_compatibility_rulebook import CropTypeSeasonCompatibilityRulebook


class CompatibilityRulesRepository:

    # Climate Compatibility (key: crop_id)
    @staticmethod
    def get_all_climate_compatibility() -> list:
        return ClimateCompatibilityRulebook.query.all()

    @staticmethod
    def get_climate_compatibility_by_crop(crop_id: int) -> ClimateCompatibilityRulebook:
        return ClimateCompatibilityRulebook.query.filter_by(crop_id=crop_id).first()

    # Soil Climate Compatibility (key: crop_id)
    @staticmethod
    def get_all_soil_climate_compatibility() -> list:
        return SoilClimateCompatibilityRulebook.query.all()

    @staticmethod
    def get_soil_climate_compatibility_by_crop(crop_id: int) -> SoilClimateCompatibilityRulebook:
        return SoilClimateCompatibilityRulebook.query.filter_by(crop_id=crop_id).first()

    # Crop Soil Compatibility (keys: crop_id, soil_type_id)
    @staticmethod
    def get_all_crop_soil_compatibility() -> list:
        return CropSoilCompatibilityRulebook.query.all()

    @staticmethod
    def get_crop_soil_compatibility_by_crop(crop_id: int) -> list:
        return CropSoilCompatibilityRulebook.query.filter_by(crop_id=crop_id).all()

    @staticmethod
    def get_crop_soil_compatibility_by_crop_and_soil(crop_id: int, soil_type_id: int) -> CropSoilCompatibilityRulebook:
        return CropSoilCompatibilityRulebook.query.filter_by(crop_id=crop_id, soil_type_id=soil_type_id).first()

    # Crop Season Compatibility (keys: crop_id, season)
    @staticmethod
    def get_all_crop_season_compatibility() -> list:
        return CropSeasonCompatibilityRulebook.query.all()

    @staticmethod
    def get_crop_season_compatibility_by_crop(crop_id: int) -> list:
        return CropSeasonCompatibilityRulebook.query.filter_by(crop_id=crop_id).all()

    @staticmethod
    def get_crop_season_compatibility_by_crop_and_season(crop_id: int, season: str) -> CropSeasonCompatibilityRulebook:
        return CropSeasonCompatibilityRulebook.query.filter_by(crop_id=crop_id, season=season).first()

    # Water Source Compatibility (keys: crop_id, water_source_id)
    @staticmethod
    def get_all_water_source_compatibility() -> list:
        return WaterSourceCompatibilityRulebook.query.all()

    @staticmethod
    def get_water_source_compatibility_by_crop(crop_id: int) -> list:
        return WaterSourceCompatibilityRulebook.query.filter_by(crop_id=crop_id).all()

    @staticmethod
    def get_water_source_compatibility_by_crop_and_source(crop_id: int, water_source_id: int) -> WaterSourceCompatibilityRulebook:
        return WaterSourceCompatibilityRulebook.query.filter_by(crop_id=crop_id, water_source_id=water_source_id).first()

    # Irrigation Frequency Compatibility (key: crop_id)
    @staticmethod
    def get_all_irrigation_frequency_compatibility() -> list:
        return IrrigationFrequencyCompatibilityRulebook.query.all()

    @staticmethod
    def get_irrigation_frequency_compatibility_by_crop(crop_id: int) -> IrrigationFrequencyCompatibilityRulebook:
        return IrrigationFrequencyCompatibilityRulebook.query.filter_by(crop_id=crop_id).first()

    # Crop Type Season Compatibility (keys: crop_type_id, season)
    @staticmethod
    def get_all_crop_type_season_compatibility() -> list:
        return CropTypeSeasonCompatibilityRulebook.query.all()

    @staticmethod
    def get_crop_type_season_compatibility_by_type(crop_type_id: int) -> list:
        return CropTypeSeasonCompatibilityRulebook.query.filter_by(crop_type_id=crop_type_id).all()

    @staticmethod
    def get_crop_type_season_compatibility_by_type_and_season(crop_type_id: int, season: str) -> CropTypeSeasonCompatibilityRulebook:
        return CropTypeSeasonCompatibilityRulebook.query.filter_by(crop_type_id=crop_type_id, season=season).first()
