from app.extensions import db
from app.rules.vocabulary.crop_names   import CropNames
from app.rules.vocabulary.crop_type    import CropType
from app.rules.vocabulary.soil_type    import Soil_Type
from app.rules.vocabulary.growth_stage import GrowthStage
from app.rules.vocabulary.water_source import WaterSource
from app.rules.vocabulary.season_names import SeasonNames
from app.rules.vocabulary.mappings import get_vocabulary


class VocabularySeeder:

    def __init__(self, db):
        self.db = db

    def seed_all(self):
        vocab = get_vocabulary()

        self._clear_tables()

        self._seed(CropType,    vocab['Crop_Type'],    'name')
        self._seed(CropNames,   vocab['Crop_Name'],    'name')
        self._seed(GrowthStage, vocab['Growth_Stage'], 'name')
        self._seed(Soil_Type,   vocab['Soil_Type'],    'name')
        self._seed(WaterSource, vocab['Water_Source'], 'name')
        self._seed(SeasonNames, vocab['Season'],       'name')

        self.db.session.commit()

    def _seed(self, model, mapping: dict, name_field: str):
        self.db.session.bulk_save_objects(
            [model(id=k, **{name_field: v}) for k, v in mapping.items()]
        )

    def _clear_tables(self):
        CropNames.query.delete()
        CropType.query.delete()
        Soil_Type.query.delete()
        GrowthStage.query.delete()
        WaterSource.query.delete()
        SeasonNames.query.delete()


def run():
    seeder = VocabularySeeder(db)
    seeder.seed_all()
