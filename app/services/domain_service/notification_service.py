from app.repositories.notification_repository import NotificationRepository
from app.models.notification import Notification


class NotificationService:

    @staticmethod
    def create(
        user_id: int,
        title: str,
        message: str,
        notification_type: str,
        detail: str = None,
        entity_type: str = None,
        entity_id: int = None,
    ) -> Notification:
        return NotificationRepository.create({
            "user_id": user_id,
            "title": title,
            "message": message,
            "notification_type": notification_type,
            "detail": detail,
            "entity_type": entity_type,
            "entity_id": entity_id,
        })

    @staticmethod
    def create_if_not_duplicate(
        user_id: int,
        title: str,
        message: str,
        notification_type: str,
        detail: str = None,
        entity_type: str = None,
        entity_id: int = None,
        within_minutes: int = 30,
    ) -> Notification | None:
        """Create only if no identical notification exists within the dedup window."""
        if NotificationRepository.recent_duplicate_exists(
            user_id, notification_type, message, within_minutes
        ):
            return None
        return NotificationService.create(
            user_id, title, message, notification_type, detail, entity_type, entity_id
        )

    @staticmethod
    def get_paginated(user_id: int, page: int = 1, per_page: int = 20, notification_type: str = None):
        return NotificationRepository.get_paginated(user_id, page, per_page, notification_type)

    @staticmethod
    def get_by_type(user_id: int, notification_type: str) -> list:
        return NotificationRepository.get_by_type(user_id, notification_type)

    @staticmethod
    def get_unread(user_id: int) -> list:
        return NotificationRepository.get_unread(user_id)

    @staticmethod
    def get_unread_critical(user_id: int) -> list:
        return NotificationRepository.get_unread_critical(user_id)

    @staticmethod
    def get_unread_count(user_id: int) -> int:
        return NotificationRepository.get_unread_count(user_id)

    @staticmethod
    def mark_as_read(notification_id: int):
        return NotificationRepository.mark_as_read(notification_id)

    @staticmethod
    def mark_all_read(user_id: int) -> None:
        NotificationRepository.mark_all_read(user_id)

    @staticmethod
    def delete(notification_id: int):
        return NotificationRepository.delete(notification_id)
