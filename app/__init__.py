from flask import Flask
from config import Config
from app.extensions import db, admin
from flask_admin.contrib.sqla import ModelView
from app.models.crop import Crop
from app.routes import register_routes

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    admin.init_app(app)
    admin.add_view(ModelView(Crop, db.session))

    register_routes(app)

    return app