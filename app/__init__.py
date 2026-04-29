from flask import Flask
from config import Config
from app.extensions import db, migrate, admin
from flask_admin.contrib.sqla import ModelView
from app.models.crop import Crop
from app.models.field import Field
from app.routes import register_routes
from app.jobs.scheduler import start_scheduler

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    admin.init_app(app)
    admin.add_view(ModelView(Crop, db.session))
    admin.add_view(ModelView(Field, db.session))
    register_routes(app)

    start_scheduler(app)

    return app