from app.rules.vocabulary.crop_names import CropNames
from app.rules.vocabulary.crop_type import CropType
from app.rules.vocabulary.growth_stage import GrowthStage
from app.rules.vocabulary.season_names import SeasonNames
from app.rules.vocabulary.soil_type import Soil_Type
from app.rules.vocabulary.water_source import WaterSource
import app.rules.vocabulary.mappings as mappings


class VocabularyRepository():

    # Crop Names
    @staticmethod
    def get_crop_by_name(name: str) -> CropNames:
        return CropNames.query.filter_by(name=name.title()).first()

    @staticmethod
    def get_crop_by_id(crop_id: int) -> CropNames:
        return CropNames.query.filter_by(id=crop_id).first()

    @staticmethod
    def get_all_crop_mapping() -> dict:
        return mappings.get_vocabulary()["Crop_Name"]

    # Crop Types
    @staticmethod
    def get_crop_type_by_name(name: str) -> CropType:
        return CropType.query.filter_by(name=name.title()).first()

    @staticmethod
    def get_crop_type_by_id(crop_type_id: int) -> CropType:
        return CropType.query.filter_by(id=crop_type_id).first()

    @staticmethod
    def get_all_crop_type_mapping() -> dict:
        return mappings.get_vocabulary()["Crop_Type"]

    # Growth Stage
    @staticmethod
    def get_stage_by_name(name: str) -> GrowthStage:
        return GrowthStage.query.filter_by(name=name.title()).first()

    @staticmethod
    def get_stage_by_id(stage_id: int) -> GrowthStage:
        return GrowthStage.query.filter_by(id=stage_id).first()

    @staticmethod
    def get_all_stage_mapping() -> dict:
        return mappings.get_vocabulary()["Growth_Stage"]

    # Seasons
    @staticmethod
    def get_season_by_name(name: str) -> SeasonNames:
        return SeasonNames.query.filter_by(name=name.title()).first()

    @staticmethod
    def get_season_by_id(season_id: int) -> SeasonNames:
        return SeasonNames.query.filter_by(id=season_id).first()

    @staticmethod
    def get_all_season_mapping() -> dict:
        return mappings.get_vocabulary()["Season"]

    # Soil Type
    @staticmethod
    def get_soil_by_name(name: str) -> Soil_Type:
        return Soil_Type.query.filter_by(name=name.title()).first()

    @staticmethod
    def get_soil_by_id(soil_id: int) -> Soil_Type:
        return Soil_Type.query.filter_by(id=soil_id).first()

    @staticmethod
    def get_all_soil_mapping() -> dict:
        return mappings.get_vocabulary()["Soil_Type"]

    # Water Source
    @staticmethod
    def get_water_source_by_name(name: str) -> WaterSource:
        return WaterSource.query.filter_by(name=name.title()).first()

    @staticmethod
    def get_water_source_by_id(water_source_id: int) -> WaterSource:
        return WaterSource.query.filter_by(id=water_source_id).first()

    @staticmethod
    def get_all_water_source_mapping() -> dict:
        return mappings.get_vocabulary()["Water_Source"]

    # Crop → Crop Type (from CROP_TYPE_MAP)
    @staticmethod
    def get_all_crop_type_crops() -> dict:
        return mappings.CROP_TYPE_MAP

    @staticmethod
    def get_crop_type_by_crop(crop_name: str) -> int | None:
        return mappings.CROP_TYPE_MAP.get(crop_name.title())

    # Season → Months (from SEASON_MONTHS)
    @staticmethod
    def get_all_season_month() -> dict:
        return mappings.SEASON_MONTHS

    @staticmethod
    def get_month_by_season(season_name: str) -> dict | None:
        return mappings.SEASON_MONTHS.get(season_name.title())
