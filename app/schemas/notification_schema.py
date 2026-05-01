from marshmallow import Schema, fields, post_dump

# Notification metadata: symbol, color, and UI presentation
NOTIFICATION_METADATA = {
    "info": {
        "symbol": "ℹ️",
        "color": "#2196F3",
        "bg_color": "#E3F2FD",
        "label": "Information",
    },
    "warning": {
        "symbol": "⚠️",
        "color": "#FF9800",
        "bg_color": "#FFF3E0",
        "label": "Warning",
    },
    "critical": {
        "symbol": "🚨",
        "color": "#F44336",
        "bg_color": "#FFEBEE",
        "label": "Alert",
    },
    "recommendation": {
        "symbol": "💡",
        "color": "#4CAF50",
        "bg_color": "#E8F5E9",
        "label": "Recommendation",
    },
}


class NotificationSchema(Schema):
    id = fields.Int()
    user_id = fields.Int()
    title = fields.Str()
    message = fields.Str()
    detail = fields.Str(allow_none=True)
    notification_type = fields.Str()
    is_read = fields.Bool()
    created_at = fields.DateTime()
    entity_type = fields.Str(allow_none=True)
    entity_id = fields.Int(allow_none=True)

    @post_dump
    def add_metadata(self, data, **kwargs):
        """Attach UI metadata based on notification type."""
        notification_type = data.get("notification_type", "info")
        metadata = NOTIFICATION_METADATA.get(notification_type, NOTIFICATION_METADATA["info"])
        data["symbol"] = metadata["symbol"]
        data["color"] = metadata["color"]
        data["bg_color"] = metadata["bg_color"]
        data["label"] = metadata["label"]
        return data


class NotificationListResponseSchema(Schema):
    notifications = fields.List(fields.Nested(NotificationSchema))
    total = fields.Int()
    unread_count = fields.Int()
    page = fields.Int()
    pages = fields.Int()
    has_next = fields.Bool()


class UnreadNotificationsResponseSchema(Schema):
    notifications = fields.List(fields.Nested(NotificationSchema))
    unread_count = fields.Int()
