from app.repositories.user_repository import UserRepository

class UserService:
    @staticmethod
    def create_user(data):
        return UserRepository.create(data)

    @staticmethod
    def get_all_users():
        return UserRepository.get_all()

    @staticmethod
    def get_user_by_id(user_id):
        return UserRepository.get_by_id(user_id)

    @staticmethod
    def delete_user(user_id):
        user = UserRepository.get_by_id(user_id)
        if user:
            UserRepository.delete(user)
        return user