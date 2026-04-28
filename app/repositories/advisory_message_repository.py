from app.models.advisory_message import AdvisoryMessage
from app.extensions import db

class AdvisoryMessageRepository:
    @staticmethod
    def create(data):
        advisory_message = AdvisoryMessage(**data)
        db.session.add(advisory_message)
        db.session.commit()
        return advisory_message

    @staticmethod
    def get_all():
        return AdvisoryMessage.query

    @staticmethod
    def get_by_id(advisory_message_id):
        return AdvisoryMessage.query.get(advisory_message_id)

    @staticmethod
    def delete(advisory_message):
        db.session.delete(advisory_message)
        db.session.commit()

    @staticmethod
    def update(advisory_message, data):    
        for key, value in data.items():
            setattr(advisory_message, key, value)
        db.session.commit()
        return advisory_message