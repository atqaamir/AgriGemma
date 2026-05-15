from app.extensions import db


class IrrigationFrequencyRulebook(db.Model):
    __tablename__ = "irrigation_frequency_rulebook"

    id = db.Column(db.Integer, primary_key=True)
    crop_id = db.Column(db.Integer, nullable = False)
    growth_stage_id = db.Column(db.Integer, nullable = False)

    recommended_frequency = db.Column(db.Integer)


    def get_irrigation(crop, growth_stage, soil_type):
        pass
