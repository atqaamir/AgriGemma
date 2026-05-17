from app.models.user import User
from app.extensions import db       

class UserRepository:
    @staticmethod
    def create(data):
        user = User(**data)
        db.session.add(user)
        db.session.commit()
        return user

    @staticmethod
    def get_all():
        return User.query.all()

    @staticmethod
    def get_by_id(user_id):
        return User.query.get(user_id)

    @staticmethod
    def delete(user):
        db.session.delete(user)
        db.session.commit()

    @staticmethod
    def update(user, data):    
        for key, value in data.items():
            setattr(user, key, value)
        db.session.commit()
        return user