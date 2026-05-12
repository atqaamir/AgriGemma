from app.extensions import db


class ThresholdRulebook(db.Model):
    __tablename__ = "threshold_rulebook"

    id = db.Column(db.Integer, primary_key=True)
    crop_id = db.Column(db.Integer, nullable = False)
    growth_stage_id = db.Column(db.Integer, nullable = False)

    frost_risk_caution = db.Column(db.Float)
    frost_risk_critical = db.Column(db.Float)
    wind_caution = db.Column(db.Float)
    wind_critical = db.Column(db.Float)

    temp_cold_caution = db.Column(db.Float)
    temp_cold_critical = db.Column(db.Float)
    temp_heat_caution = db.Column(db.Float)
    temp_heat_critical = db.Column(db.Float)


    def check_frost(crop, growth_stage, frost_risk_value):
        pass

    def check_wind(crop, growth_stage, wind_speed_value):
        pass

    def check_temperature(crop, growth_stage, temp_value):
        pass

    def check_all(crop, growth_stage, frost_risk, wind_speed, temperature):
        pass