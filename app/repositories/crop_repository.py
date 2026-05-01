from app.models.crop import Crop
from app.extensions import db

class CropRepository:

    @staticmethod
    def create(data):
        crop = Crop(**data)
        db.session.add(crop)
        db.session.commit()
        return crop

    @staticmethod
    def get_all():
        return Crop.query

    @staticmethod
    def get_by_id(crop_id):
        return Crop.query.get(crop_id)

    @staticmethod
    def delete(crop):
        db.session.delete(crop)
        db.session.commit()

    @staticmethod
    def update(crop, data):
        for key, value in data.items():
            setattr(crop, key, value)
        db.session.commit()
        return crop

    @staticmethod
    def get_by_user_id(user_id):
        return Crop.query.filter_by(user_id=user_id).all()


"""       
DO NOT DO THIS -> AN EXAMPLE OF BUSINESS LOGIC THAT SHOULD BE IN THE SERVICE LAYER, NOT THE REPOSITORY LAYER
class CropRepository:
    def needs_irrigation(crop):
        return crop.water_requirement > 50
"""