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


# Nullable columns added to existing tables after the first deploy. db.create_all()
# only creates missing tables, so add these columns if an existing DB lacks them.
ADDED_COLUMNS = [
    ("task", "completed_at", "TIMESTAMP"),
]


def ensure_added_columns():
    from sqlalchemy import inspect, text

    inspector = inspect(db.engine)
    for table, column, sql_type in ADDED_COLUMNS:
        existing = {c["name"] for c in inspector.get_columns(table)}
        if column not in existing:
            with db.engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {sql_type}"))
            print(f"Added missing column {table}.{column}")


def bootstrap():
    app = create_app()

    with app.app_context():
        db.create_all()
        ensure_added_columns()
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
