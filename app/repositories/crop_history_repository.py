from models.crop_history import CropHistory
from app.extensions import db

class CropHistoryRepository:
    @staticmethod
    def create(data):
        crop_history = CropHistory(**data)
        db.session.add(crop_history)
        db.session.commit()
        return crop_history

    @staticmethod
    def get_all():
        return CropHistory.query

    @staticmethod
    def get_by_id(crop_history_id):
        return CropHistory.query.get(crop_history_id)

    @staticmethod
    def delete(crop_history):
        db.session.delete(crop_history)
        db.session.commit()