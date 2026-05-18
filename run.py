import os

from app import create_app
from app.extensions import db

from app.rules.rule_engine.populate_vocabulary import run as populate_vocabulary_run
from app.rules.rule_engine.create_rulebooks import run as populate_rulebooks_run
from Test_Runs.seed_data import run as seed_data_run
from Test_Runs.populate_seasonal_plan import run as populate_seasonal_plan_run
from Test_Runs.populate_weekly_plan import run as populate_weekly_plan_run


def reset_database(db_path="app.db"):
    if os.path.exists(db_path):
        os.remove(db_path)


def bootstrap():
    app = create_app()

    with app.app_context():
        db.create_all()
        populate_vocabulary_run()
        populate_rulebooks_run(db)
        seed_data_run()
        populate_seasonal_plan_run()
        populate_weekly_plan_run()

    return app


# IMPORTANT: global app variable for gunicorn
app = bootstrap()


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000, threaded=True)
