from datetime import datetime, timedelta

from app.models.notification import Notification
from app.extensions import db


class NotificationRepository:

    @staticmethod
    def create(data: dict) -> Notification:
        notification = Notification(**data)
        db.session.add(notification)
        db.session.commit()
        return notification

    @staticmethod
    def recent_duplicate_exists(
        user_id: int,
        notification_type: str,
        message: str,
        within_minutes: int = 30,
    ) -> bool:
        """Prevent the same message from spamming the user within the window."""
        cutoff = datetime.utcnow() - timedelta(minutes=within_minutes)
        return (
            Notification.query.filter(
                Notification.user_id == user_id,
                Notification.notification_type == notification_type,
                Notification.message == message,
                Notification.created_at >= cutoff,
            ).count()
            > 0
        )

    @staticmethod
    def get_paginated(user_id: int, page: int = 1, per_page: int = 20, notification_type: str = None):
        query = Notification.query.filter_by(user_id=user_id)
        if notification_type:
            query = query.filter_by(notification_type=notification_type)
        return query.order_by(Notification.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

    @staticmethod
    def get_by_type(user_id: int, notification_type: str) -> list:
        return (
            Notification.query
            .filter_by(user_id=user_id, notification_type=notification_type)
            .order_by(Notification.created_at.desc())
            .all()
        )

    @staticmethod
    def get_unread(user_id: int) -> list:
        return (
            Notification.query
            .filter_by(user_id=user_id, is_read=False)
            .order_by(Notification.created_at.desc())
            .all()
        )

    @staticmethod
    def get_unread_critical(user_id: int) -> list:
        return (
            Notification.query
            .filter_by(user_id=user_id, is_read=False)
            .filter(Notification.notification_type.in_(["critical", "alert", "change"]))
            .order_by(Notification.created_at.desc())
            .all()
        )

    @staticmethod
    def get_unread_count(user_id: int) -> int:
        return Notification.query.filter_by(user_id=user_id, is_read=False).count()

    @staticmethod
    def get_by_id(notification_id: int):
        return Notification.query.get(notification_id)

    @staticmethod
    def mark_as_read(notification_id: int):
        notification = Notification.query.get(notification_id)
        if notification:
            notification.is_read = True
            db.session.commit()
        return notification

    @staticmethod
    def mark_all_read(user_id: int) -> None:
        Notification.query.filter_by(user_id=user_id, is_read=False).update({"is_read": True})
        db.session.commit()

    @staticmethod
    def delete(notification_id: int):
        notification = Notification.query.get(notification_id)
        if notification:
            db.session.delete(notification)
            db.session.commit()
        return notification
