from flask import Blueprint, request, jsonify, render_template

from app.services.domain_service.notification_service import NotificationService
from app.schemas.notification_schema import NotificationSchema

notifications_bp = Blueprint("notifications_bp", __name__)

notification_schema = NotificationSchema()
notifications_schema = NotificationSchema(many=True)


# ── Page ─────────────────────────────────────────────────────────────────────

@notifications_bp.route("/page", methods=["GET"])
def notifications_page():
    return render_template("notifications.html")


# ── Collection endpoints ──────────────────────────────────────────────────────

@notifications_bp.route("/", methods=["GET"])
def get_notifications():
    """
    Paginated notification list.
    Query params:
      user_id           int   (default 1)
      page              int   (default 1)
      per_page          int   (default 20, max 100)
      type              str   info | warning | critical | recommendation  (optional)
    """
    user_id = request.args.get("user_id", 1, type=int)
    notification_type = request.args.get("type")

    if notification_type:
        items = NotificationService.get_by_type(user_id, notification_type)
        return jsonify({
            "notifications": notifications_schema.dump(items),
            "total": len(items),
            "unread_count": NotificationService.get_unread_count(user_id),
        }), 200

    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    paginated = NotificationService.get_paginated(user_id, page, per_page)

    return jsonify({
        "notifications": notifications_schema.dump(paginated.items),
        "total": paginated.total,
        "unread_count": NotificationService.get_unread_count(user_id),
        "page": paginated.page,
        "pages": paginated.pages,
        "has_next": paginated.has_next,
    }), 200


@notifications_bp.route("/unread", methods=["GET"])
def get_unread():
    user_id = request.args.get("user_id", 1, type=int)
    items = NotificationService.get_unread(user_id)
    return jsonify({
        "notifications": notifications_schema.dump(items),
        "unread_count": len(items),
    }), 200


@notifications_bp.route("/unread/count", methods=["GET"])
def get_unread_count():
    user_id = request.args.get("user_id", 1, type=int)
    return jsonify({"unread_count": NotificationService.get_unread_count(user_id)}), 200


@notifications_bp.route("/unread/critical", methods=["GET"])
def get_unread_critical():
    """Returns unread critical notifications — used to populate the alert popup queue."""
    user_id = request.args.get("user_id", 1, type=int)
    items = NotificationService.get_unread_critical(user_id)
    return jsonify({"notifications": notifications_schema.dump(items)}), 200


# ── Mutation endpoints ────────────────────────────────────────────────────────

@notifications_bp.route("/<int:notification_id>/read", methods=["PUT"])
def mark_as_read(notification_id):
    notification = NotificationService.mark_as_read(notification_id)
    if not notification:
        return jsonify({"error": "Notification not found"}), 404
    return jsonify(notification_schema.dump(notification)), 200


@notifications_bp.route("/read-all", methods=["PUT"])
def mark_all_read():
    user_id = request.args.get("user_id", 1, type=int)
    NotificationService.mark_all_read(user_id)
    return jsonify({"message": "All notifications marked as read"}), 200


@notifications_bp.route("/test/create", methods=["POST"])
def create_test_notification():
    """
    Test endpoint to create test notifications.
    Use for testing the notification UI.

    POST /notifications/test/create
    Body: {
        "user_id": 1,
        "title": "Test Alert",
        "message": "This is a test notification",
        "notification_type": "critical"
    }
    """
    data = request.get_json() or {}
    user_id = data.get("user_id", 1)
    title = data.get("title", "Test Notification")
    message = data.get("message", "This is a test message")
    notification_type = data.get("notification_type", "info")
    detail = data.get("detail", f"Test detail for {title}")

    notification = NotificationService.create(
        user_id=user_id,
        title=title,
        message=message,
        notification_type=notification_type,
        detail=detail,
    )

    return jsonify(notification_schema.dump(notification)), 201

