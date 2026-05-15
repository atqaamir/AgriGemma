from app.rules.rulebooks.action_rules.soil_action_rulebook import SoilActionRulebook
from app.rules.rulebooks.action_rules.season_action_rulebook import SeasonActionRulebook
from app.rules.rulebooks.action_rules.temperature_action_rulebook import TemperatureActionRulebook
from app.rules.rulebooks.action_rules.humidity_action_rulebook import HumidityActionRulebook
from app.rules.rulebooks.action_rules.soil_moisture_action_rulebook import SoilMoistureActionRulebook
from app.rules.rulebooks.action_rules.ph_action_rulebook import PhActionRulebook
from app.rules.rulebooks.action_rules.sunlight_action_rulebook import SunlightActionRulebook
from app.rules.rulebooks.action_rules.water_source_action_rulebook import WaterSourceActionRulebook
from app.rules.rulebooks.action_rules.rainfall_action_rulebook import RainfallActionRulebook


class ActionRulesRepository:

    # Soil Action (keys: crop_id, soil_type_id)
    @staticmethod
    def get_all_soil_actions() -> list:
        return SoilActionRulebook.query.all()

    @staticmethod
    def get_soil_action_by_crop(crop_id: int) -> list:
        return SoilActionRulebook.query.filter_by(crop_id=crop_id).all()

    @staticmethod
    def get_soil_action_by_crop_and_soil(crop_id: int, soil_type_id: int) -> SoilActionRulebook:
        return SoilActionRulebook.query.filter_by(crop_id=crop_id, soil_type_id=soil_type_id).first()

    # Season Action (keys: crop_id, season_id)
    @staticmethod
    def get_all_season_actions() -> list:
        return SeasonActionRulebook.query.all()

    @staticmethod
    def get_season_action_by_crop(crop_id: int) -> list:
        return SeasonActionRulebook.query.filter_by(crop_id=crop_id).all()

    @staticmethod
    def get_season_action_by_crop_and_season(crop_id: int, season_id: int) -> SeasonActionRulebook:
        return SeasonActionRulebook.query.filter_by(crop_id=crop_id, season_id=season_id).first()

    # Temperature Action (keys: crop_id, growth_stage_id, temp_range)
    @staticmethod
    def get_all_temperature_actions() -> list:
        return TemperatureActionRulebook.query.all()

    @staticmethod
    def get_temperature_action_by_crop(crop_id: int) -> list:
        return TemperatureActionRulebook.query.filter_by(crop_id=crop_id).all()

    @staticmethod
    def get_temperature_action_by_crop_and_range(crop_id: int, growth_stage_id: int, temp_range: str) -> TemperatureActionRulebook:
        return TemperatureActionRulebook.query.filter_by(crop_id=crop_id, growth_stage_id=growth_stage_id, temp_range=temp_range).first()

    # Humidity Action (keys: crop_id, growth_stage_id, humidity_range)
    @staticmethod
    def get_all_humidity_actions() -> list:
        return HumidityActionRulebook.query.all()

    @staticmethod
    def get_humidity_action_by_crop(crop_id: int) -> list:
        return HumidityActionRulebook.query.filter_by(crop_id=crop_id).all()

    @staticmethod
    def get_humidity_action_by_crop_and_range(crop_id: int, growth_stage_id: int, humidity_range: str) -> HumidityActionRulebook:
        return HumidityActionRulebook.query.filter_by(crop_id=crop_id, growth_stage_id=growth_stage_id, humidity_range=humidity_range).first()

    # Soil Moisture Action (keys: crop_id, growth_stage_id, moisture_range)
    @staticmethod
    def get_all_soil_moisture_actions() -> list:
        return SoilMoistureActionRulebook.query.all()

    @staticmethod
    def get_soil_moisture_action_by_crop(crop_id: int) -> list:
        return SoilMoistureActionRulebook.query.filter_by(crop_id=crop_id).all()

    @staticmethod
    def get_soil_moisture_action_by_crop_and_range(crop_id: int, growth_stage_id: int, moisture_range: str) -> SoilMoistureActionRulebook:
        return SoilMoistureActionRulebook.query.filter_by(crop_id=crop_id, growth_stage_id=growth_stage_id, moisture_range=moisture_range).first()

    # pH Action (keys: crop_id, growth_stage_id, ph_category)
    @staticmethod
    def get_all_ph_actions() -> list:
        return PhActionRulebook.query.all()

    @staticmethod
    def get_ph_action_by_crop(crop_id: int) -> list:
        return PhActionRulebook.query.filter_by(crop_id=crop_id).all()

    @staticmethod
    def get_ph_action_by_crop_and_category(crop_id: int, growth_stage_id: int, ph_category: str) -> PhActionRulebook:
        return PhActionRulebook.query.filter_by(crop_id=crop_id, growth_stage_id=growth_stage_id, ph_category=ph_category).first()

    # Sunlight Action (keys: crop_id, growth_stage_id, sunlight_range)
    @staticmethod
    def get_all_sunlight_actions() -> list:
        return SunlightActionRulebook.query.all()

    @staticmethod
    def get_sunlight_action_by_crop(crop_id: int) -> list:
        return SunlightActionRulebook.query.filter_by(crop_id=crop_id).all()

    @staticmethod
    def get_sunlight_action_by_crop_and_range(crop_id: int, growth_stage_id: int, sunlight_range: str) -> SunlightActionRulebook:
        return SunlightActionRulebook.query.filter_by(crop_id=crop_id, growth_stage_id=growth_stage_id, sunlight_range=sunlight_range).first()

    # Water Source Action (keys: crop_id, water_source_id)
    @staticmethod
    def get_all_water_source_actions() -> list:
        return WaterSourceActionRulebook.query.all()

    @staticmethod
    def get_water_source_action_by_crop(crop_id: int) -> list:
        return WaterSourceActionRulebook.query.filter_by(crop_id=crop_id).all()

    @staticmethod
    def get_water_source_action_by_crop_and_source(crop_id: int, water_source_id: int) -> WaterSourceActionRulebook:
        return WaterSourceActionRulebook.query.filter_by(crop_id=crop_id, water_source_id=water_source_id).first()

    # Rainfall Action (keys: crop_id, growth_stage_id, rainfall_range)
    @staticmethod
    def get_all_rainfall_actions() -> list:
        return RainfallActionRulebook.query.all()

    @staticmethod
    def get_rainfall_action_by_crop(crop_id: int) -> list:
        return RainfallActionRulebook.query.filter_by(crop_id=crop_id).all()

    @staticmethod
    def get_rainfall_action_by_crop_and_range(crop_id: int, growth_stage_id: int, rainfall_range: str) -> RainfallActionRulebook:
        return RainfallActionRulebook.query.filter_by(crop_id=crop_id, growth_stage_id=growth_stage_id, rainfall_range=rainfall_range).first()
