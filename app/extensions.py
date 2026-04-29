from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_admin import Admin

db = SQLAlchemy()
migrate = Migrate(render_as_batch=True)
admin = Admin(name="Smart Farming Admin")