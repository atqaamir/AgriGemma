from app.extensions import db
from app.rules.Vocubualry.crop_names import CropNames
from app.rules.Vocubualry.soil_type import Soil_Type
from app.rules.Vocubualry.growth_stage import GrowthStage
from app.rules.Vocubualry.water_source import WaterSource


def get_vocabulary():
    return {
        "Crop_Name": {
            1: "Maize",
            2: "Rice",
            3: "Cotton"
        },
        "Growth_Stage": {
            1: "Seedling",
            2: "Vegetative",
            3: "Flowering"
        },
        "Soil_Type": {
            1: "Sandy",
            2: "Loamy",
            3: "Clay"
        },
        "Water_Source": {
            1: "River",
            2: "Groundwater",
            3: "Recycled"
        }
    }


class VocabularySeeder:

    def __init__(self, db):
        self.db = db

    def seed_all(self):
        vocab = get_vocabulary()

        self._clear_tables()

        self._seed(CropNames, vocab["Crop_Name"], "name")
        self._seed(GrowthStage, vocab["Growth_Stage"], "name")
        self._seed(Soil_Type, vocab["Soil_Type"], "name")
        self._seed(WaterSource, vocab["Water_Source"], "name")

        self.db.session.commit()

    def _seed(self, model, mapping: dict, name_field: str):
        objects = [
            model(id=k, **{name_field: v})
            for k, v in mapping.items()
        ]
        self.db.session.bulk_save_objects(objects)

    def _clear_tables(self):
        CropNames.query.delete()
        Soil_Type.query.delete()
        GrowthStage.query.delete()
        WaterSource.query.delete()


def run():
    seeder = VocabularySeeder(db)
    seeder.seed_all()