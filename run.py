import logging
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


logger = logging.getLogger("run")

# Nullable columns added to existing tables after the first deploy. db.create_all()
# only creates missing tables, so these are added if an existing DB lacks them.
# The column type comes from the SQLAlchemy model.
ADDED_COLUMNS = [
    ("task", "completed_at"),
    ("task", "seasonal_plan_entry_id"),
    ("task", "changed_on"),
    ("seasonal_plan_entry", "skipped_on"),
]


def ensure_added_columns():
    """Add missing *nullable* columns listed in ADDED_COLUMNS (SQLite and Postgres).

    Only ever runs `ALTER TABLE <table> ADD COLUMN <column> <type>`. It never drops,
    renames or alters anything; a non-nullable column is refused (needs a migration).
    """
    from sqlalchemy import inspect, text

    engine = db.engine
    inspector = inspect(engine)
    quote = engine.dialect.identifier_preparer.quote
    existing_tables = set(inspector.get_table_names())

    for table_name, column_name in ADDED_COLUMNS:
        table = db.metadata.tables.get(table_name)
        column = table.columns.get(column_name) if table is not None else None
        if column is None:
            logger.error("Schema check: %s.%s is not defined in the models — skipped", table_name, column_name)
            continue
        if not column.nullable or column.primary_key:
            logger.error("Schema check: %s.%s is not nullable — refusing ADD COLUMN, needs a real migration",
                         table_name, column_name)
            continue
        if table_name not in existing_tables:
            continue   # create_all() has just created the whole table
        if column_name in {c["name"] for c in inspector.get_columns(table_name)}:
            continue

        col_type = column.type.compile(dialect=engine.dialect)
        sql = f"ALTER TABLE {quote(table_name)} ADD COLUMN {quote(column_name)} {col_type}"
        with engine.begin() as conn:
            conn.execute(text(sql))
        logger.warning("Schema check: added nullable column %s.%s (%s) on %s",
                       table_name, column_name, col_type, engine.dialect.name)
        print(f"Added missing column {table_name}.{column_name} ({col_type}) on {engine.dialect.name}")


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
        apply_startup_forecast()

    return app


def apply_startup_forecast():
    """Plan roll + forecast + plan task sync for every user; no AI calls, no notifications
    (shared with "Reset demo": app/services/demo_reset_service.py)."""
    from app.services.demo_reset_service import apply_startup_forecast as _apply
    _apply()


# IMPORTANT: global app variable for gunicorn
app = bootstrap()


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000, threaded=True)
