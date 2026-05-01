# Smart Farming Notification & Intelligence System

## System Overview

This document describes the complete implementation of the notification and AI intelligence system for Smart Farming.

### Core Components

1. **Notification Model** (`app/models/notification.py`)
   - Types: `info`, `warning`, `critical`, `recommendation`
   - Fields: `id`, `user_id`, `title`, `message`, `detail`, `notification_type`, `is_read`, `created_at`
   - Includes optional entity tracking (`entity_type`, `entity_id`)

2. **AI Model Service** (Modular & Provider-based)
   - Interface: `app/services/ai_model_service/ai_provider_interface.py`
   - Registry: `app/services/ai_model_service/ai_model_service.py`
   - Providers:
     - **GemmaProvider**: Production AI backend (requires Ollama/Gemma)
     - **PlaceholderProvider**: Testing backend (no external dependencies)

3. **Task Intelligence Service** (`app/services/task_intelligence_service.py`)
   - Generates AI-driven insights from task context
   - Caches results for 5 minutes to reduce API calls
   - Falls back to rule-based analysis if AI is unavailable
   - Input: Task status, pending items, weekly plan, seasonal planner, weather data
   - Output: Summary, priority level, recommendations, urgent actions, risks, insights

4. **Task Event Service** (`app/services/task_event_service.py`)
   - Fires in background on task changes (create, update, delete, mark done)
   - Runs task intelligence generation asynchronously
   - Creates `critical` and `recommendation` notifications from results
   - Prevents duplicate notifications within 30-minute window

5. **Notification UI** (`app/templates/notification_ui.html`)
   - Bell icon with red badge showing unread count
   - Dropdown showing all unread notifications
   - Color-coded and symbol-decorated notifications
   - Popup alerts for critical notifications
   - Modal details for critical and recommendation notifications
   - Auto-refreshes every 10 seconds

## Usage

### Setting Up the Development Environment

#### Option 1: Using Placeholder AI (No External Dependencies)

```bash
export USE_PLACEHOLDER_AI=true
flask run
```

The placeholder provider generates deterministic, realistic responses without requiring Gemma or any external API.

#### Option 2: Using Gemma (Production)

1. Install and run Ollama:
   ```bash
   # Download from https://ollama.ai
   ollama pull gemma3:4b
   ollama serve
   ```

2. Start the app (uses Gemma by default):
   ```bash
   flask run
   ```

You can also configure the Gemma endpoint:
```bash
export GEMMA_API_URL=http://your-ollama-server:11434/api/generate
flask run
```

### Switching Providers

The system is designed to be provider-agnostic. To add a new AI provider:

1. Create a new provider class inheriting from `AIModelProvider`:

```python
from app.services.ai_model_service.ai_provider_interface import AIModelProvider

class MyCustomProvider(AIModelProvider):
    @property
    def name(self) -> str:
        return "My Custom AI"
    
    def complete(self, prompt: str) -> str:
        # Your implementation here
        return response_text
```

2. Register it in `app/__init__.py`:

```python
def _register_ai_provider():
    from app.services.ai_model_service import ai_model_service
    from app.services.ai_model_service.my_custom_provider import MyCustomProvider
    
    ai_model_service.register_provider(MyCustomProvider())
```

### Notification Types & Display

| Type | Symbol | Color | Use Case | Behavior |
|------|--------|-------|----------|----------|
| `info` | ℹ️ | Blue | General information | Dropdown only |
| `warning` | ⚠️ | Orange | Important but non-critical | Dropdown only |
| `critical` | 🚨 | Red | Urgent alerts | Popup + Dropdown |
| `recommendation` | 💡 | Green | AI-driven suggestions | Dropdown (clickable for details) |

### Triggering Task Intelligence

Intelligence is automatically generated when:
- A task is created
- A task is updated
- A task is marked complete
- A task is deleted

Manual trigger (from code):
```python
from app.services.task_event_service import TaskEventService
from flask import current_app

TaskEventService.on_task_change(user_id, current_app._get_current_object())
```

### Creating Notifications Manually

```python
from app.services.domain_service.notification_service import NotificationService

# Create a simple notification
NotificationService.create(
    user_id=1,
    title="Field Alert",
    message="Soil moisture below threshold",
    notification_type="warning"
)

# Create with AI explanation (critical or recommendation)
NotificationService.create(
    user_id=1,
    title="Critical Action Required",
    message="Irrigation needed immediately",
    notification_type="critical",
    detail="The AI analysis detected that Field A has soil moisture at 15%, "
           "which is below the critical threshold of 20%. Immediate irrigation "
           "is recommended to prevent crop stress."
)

# Prevent duplicates (deduplicates within 30 minutes)
NotificationService.create_if_not_duplicate(
    user_id=1,
    title="Recommendation",
    message="Water Field B",
    notification_type="recommendation",
    within_minutes=30
)
```

### API Endpoints

#### Get Unread Notifications
```
GET /notifications/unread?user_id=1
```
Response:
```json
{
  "notifications": [
    {
      "id": 1,
      "user_id": 1,
      "title": "Field Alert",
      "message": "Soil moisture below threshold",
      "detail": null,
      "notification_type": "warning",
      "is_read": false,
      "created_at": "2026-04-30T10:30:00",
      "symbol": "⚠️",
      "color": "#FF9800",
      "bg_color": "#FFF3E0",
      "label": "Warning"
    }
  ],
  "unread_count": 1
}
```

#### Get Unread Count
```
GET /notifications/unread/count?user_id=1
```

#### Get Unread Critical Notifications (Alerts)
```
GET /notifications/unread/critical?user_id=1
```

#### Mark as Read
```
PUT /notifications/{id}/read
```

#### Mark All as Read
```
PUT /notifications/read-all?user_id=1
```

#### Get All Notifications (Paginated)
```
GET /notifications/?user_id=1&page=1&per_page=20&type=warning
```

### Frontend Integration

Include the notification UI in your base template:

```html
{% extends "base.html" %}

{% block content %}
  <!-- Your page content here -->
{% endblock %}
```

The `base.html` template automatically includes `notification_ui.html` which provides:
- Bell icon in header
- Dropdown notifications list
- Automatic unread count update
- Alert popups for critical notifications
- Modal details for alerts and recommendations

### Context Aggregation for Intelligence

The task intelligence receives a context dict containing:

```python
context = {
    "tasks": {
        "pending_count": int,
        "overdue_count": int,
        "critical_count": int,
        "high_priority_count": int,
        "pending_list": [
            {
                "id": int,
                "title": str,
                "priority": str,
                "due_date": str,
                "is_overdue": bool,
                "field_name": str,
                "crop_name": str,
                "status": str,
            }
        ]
    },
    "farm": {
        "active_fields": int,
        "active_fields_data": [
            {
                "id": int,
                "name": str,
                "moisture_level": float,
                "health_status": str,
                "crop": str,
            }
        ]
    },
    "weather": {
        "current": {
            "temp": float,
            "humidity": float,
            "precipitation": float,
            "condition": str,
        },
        "forecast": [
            {
                "date": str,
                "temp_high": float,
                "temp_low": float,
                "condition": str,
            }
        ]
    },
    "weekly_plan": [...],  # Planned tasks for the week
    "seasonal_plan": [...], # Seasonal schedule
    "alerts": [
        {
            "id": int,
            "message": str,
            "level": str,  # "high", "medium", "low"
        }
    ]
}
```

### Testing the System

1. **Trigger a task change** (creates recommendations):
   ```bash
   curl -X POST http://localhost:5000/mytasks/tasks \
     -H "Content-Type: application/json" \
     -d '{"title": "Water Field A", "priority": "high"}'
   ```

2. **Check notifications**:
   ```bash
   curl http://localhost:5000/notifications/unread
   ```

3. **View in browser**:
   - Navigate to any page
   - Click the 🔔 bell icon
   - See notifications in dropdown
   - Critical notifications appear as popups
   - Click alerts/recommendations to see detailed explanations

### Architecture Decisions

#### Provider Pattern
The modular provider architecture allows:
- Swapping providers with a single line change
- Testing without external dependencies
- Supporting multiple AI backends
- Environment-based provider selection

#### Background Processing
- Task intelligence runs asynchronously in a daemon thread
- HTTP responses never blocked by AI calls
- Notifications created from intelligence results
- Deduplication prevents notification spam

#### Caching
- 5-minute cache on task intelligence
- Invalidated on task changes
- Reduces load on AI provider
- Maintains freshness for rapidly changing data

#### Notification Model
- Supports multiple types with extensible metadata
- Optional detail field for rich explanations
- Entity tracking enables future drill-down
- `is_read` status enables badge counting

## Troubleshooting

### Notifications Not Appearing

1. Check that notifications are being created:
   ```bash
   curl http://localhost:5000/notifications/unread
   ```

2. Verify user_id is correct (currently hardcoded as 1)

3. Check browser console for JavaScript errors

### AI Provider Not Working

1. Check provider registration:
   ```python
   from app.services.ai_model_service import ai_model_service
   print(ai_model_service.get_provider().name)
   ```

2. For Gemma: Ensure Ollama is running
   ```bash
   curl http://localhost:11434/api/tags
   ```

3. Use placeholder provider for testing:
   ```bash
   export USE_PLACEHOLDER_AI=true
   ```

### Performance Issues

1. Check cache TTL settings in `task_intelligence_service.py`
2. Reduce notification refresh interval in `notification_ui.html`
3. Implement Redis-backed cache for multi-worker deployments

## Next Steps

- [ ] Replace hardcoded `USER_ID = 1` with auth session integration
- [ ] Add push notifications for critical alerts
- [ ] Implement notification scheduling (e.g., quiet hours)
- [ ] Add notification preferences UI
- [ ] Create admin dashboard for notification management
- [ ] Set up notification analytics
- [ ] Implement real-time notifications with WebSockets
