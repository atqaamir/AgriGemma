import os

from app import create_app
from app.extensions import db

from app.rules.rule_engine.populate_vocabulary import run as populate_vocabulary_run
from app.rules.rule_engine.create_rulebooks   import run as populate_rulebooks_run
from seed_data                                 import run as seed_data_run
from app.services.demo_scenario_service        import DemoScenarioService
from populate_seasonal_plan                    import run as populate_seasonal_plan_run
from populate_weekly_plan                      import run as populate_weekly_plan_run


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
        DemoScenarioService.setup(user_id=1)
        populate_seasonal_plan_run()
        populate_weekly_plan_run()

    return app


if __name__ == "__main__":

    # 1. delete DB
    reset_database()

    # 2–3. setup + seed
    app = bootstrap()

    # 4. run app
    app.run(debug=True, host="0.0.0.0", port=5000, threaded=True)
