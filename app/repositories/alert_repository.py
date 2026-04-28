from models.alert import Alert
from app.extensions import db

class AlertRepository:
    @staticmethod
    def create(data):
        alert = Alert(**data)
        db.session.add(alert)
        db.session.commit()
        return alert

    @staticmethod
    def get_all():
        return Alert.query

    @staticmethod
    def get_by_id(alert_id):
        return Alert.query.get(alert_id)

    @staticmethod
    def delete(alert):
        db.session.delete(alert)
        db.session.commit()