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
        """Upsert the fixed vocabulary (id → name from mappings.py).

        Never deletes: crop, field and seasonal_plan_entry rows reference these
        tables by foreign key, so a delete fails on databases that enforce FKs
        (Postgres) on every start after the first. Merging by the fixed ids keeps
        the references valid and makes repeated starts safe.
        """
        vocab = get_vocabulary()

        self._upsert(CropType,    vocab['Crop_Type'],    'name')
        self._upsert(CropNames,   vocab['Crop_Name'],    'name')
        self._upsert(GrowthStage, vocab['Growth_Stage'], 'name')
        self._upsert(Soil_Type,   vocab['Soil_Type'],    'name')
        self._upsert(WaterSource, vocab['Water_Source'], 'name')
        self._upsert(SeasonNames, vocab['Season'],       'name')

        self.db.session.commit()

    def _upsert(self, model, mapping: dict, name_field: str):
        for k, v in mapping.items():
            self.db.session.merge(model(id=k, **{name_field: v}))


def run():
    seeder = VocabularySeeder(db)
    seeder.seed_all()
