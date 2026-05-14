import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from app import create_app
from app.extensions import db

from app.rules.rule_respositories.vocabulary_repository import VocabularyRepository
from app.services.rule_base_service import rule_base_service
from app.rules.rule_engine.rule_engine import RuleEngine
from app.services.seasonal_planner_service import SeasonalPlannerService
import pandas as pd

app = create_app()

with app.app_context():
    # sow_start, sow_end = rule_base_service.get_timeline_by_crop_type(1).sow_start_month, rule_base_service.get_timeline_by_crop_type(1).sow_end_month
    plan = SeasonalPlannerService.generate_initial_plan(user_id=1, crop= "Maize", soil_type="Clay", water_source="Recycled")

    # for r in plan["irrigation_frequency"]:
    #     print (r.recommended_frequency)
    

print(plan)