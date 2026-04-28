from app.rules.rule_engine import rule_engine

decision = rule_engine.evaluate_sowing(rain_mm=20, crop="maize")