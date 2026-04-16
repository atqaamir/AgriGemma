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
        return Crop.query.all()

    @staticmethod
    def get_by_id(crop_id):
        return Crop.query.get(crop_id)

    @staticmethod
    def delete(crop):
        db.session.delete(crop)
        db.session.commit()


"""       
DO NOT DO THIS -> AN EXAMPLE OF BUSINESS LOGIC THAT SHOULD BE IN THE SERVICE LAYER, NOT THE REPOSITORY LAYER
class CropRepository:
    def needs_irrigation(crop):
        return crop.water_requirement > 50
"""