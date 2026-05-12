import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import create_app
from app.extensions import db
from app.rules.rulebooks.action_rules.irrigation_frequency_action_rulebook import IrrigationFrequencyActionRulebook
import pandas as pd

app = create_app()

with app.app_context():
    rows = IrrigationFrequencyActionRulebook.query.all()
    df = pd.DataFrame([{
        'id':             r.id,
        'crop_id':        r.crop_id,
        'irr_freq_range': r.irr_freq_range,
        'feasibility':    r.feasibility,
        'reasoning':      r.reasoning,
        'actions':        r.actions,
    } for r in rows])

print(df.to_string())