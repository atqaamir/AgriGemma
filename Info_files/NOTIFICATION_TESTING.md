# Notification System - Testing & Troubleshooting

## Quick Test

### 1. Start the app with placeholder AI (no external dependencies)
```bash
export USE_PLACEHOLDER_AI=true
flask run
```

### 2. Create a test notification
```bash
curl -X POST http://localhost:5000/notifications/test/create \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "title": "Test Alert",
    "message": "This is a test notification",
    "notification_type": "critical",
    "detail": "This is the detailed explanation shown when clicked"
  }'
```

### 3. Check the notification appears
- Navigate to http://localhost:5000 (or any page)
- Look for red 🔔 bell in header
- Should show "1" badge
- Click bell to open dropdown
- Should see your notification with 🚨 symbol

### 4. Test marking as read
- Click on the notification in the dropdown
- Should show modal with title and detail
- Click "Close" button
- Badge count should decrease
- Reload page - notification should still be marked read

### 5. Test critical alert popup
- Create another critical notification with notification_type="critical"
- Should pop up in top-right corner
- Auto-dismisses after 10 seconds
- Marked as read, so won't show again on refresh

## Testing Different Notification Types

```bash
# Info notification
curl -X POST http://localhost:5000/notifications/test/create \
  -H "Content-Type: application/json" \
  -d '{"notification_type": "info", "title": "Info", "message": "This is info"}'

# Warning notification
curl -X POST http://localhost:5000/notifications/test/create \
  -H "Content-Type: application/json" \
  -d '{"notification_type": "warning", "title": "Warning", "message": "This is a warning"}'

# Recommendation notification
curl -X POST http://localhost:5000/notifications/test/create \
  -H "Content-Type: application/json" \
  -d '{"notification_type": "recommendation", "title": "Recommendation", "message": "Water Field A", "detail": "AI recommends watering based on soil moisture data"}'
```

## Test Multi-Tab Behavior

1. Open the app in two browser tabs
2. Create a notification in one tab
3. Both tabs should see the notification (auto-refresh every 10s)
4. Click mark as read in tab 1
5. Tab 2 should update within 10 seconds
6. Reload page 2 - notification should stay marked as read

## Troubleshooting

### Notification Bell Not Working

**Problem**: Bell doesn't respond to clicks

**Solutions**:
1. Check browser console for JavaScript errors (F12 → Console tab)
2. Verify notification-ui.html is included in your template
3. Check that `notification-container` div exists
4. Try hard refresh (Ctrl+F5 or Cmd+Shift+R)

### Notifications Disappear on Refresh

**Problem**: Marked notifications reappear as unread after page reload

**Solutions**:
1. Check database connectivity: `sqlite3 instance/smartfarming.db "SELECT * FROM notification;"`
2. Verify NotificationService.mark_as_read() is being called
3. Check for errors in Flask logs
4. Clear browser cache: Ctrl+Shift+Delete, select "All time", clear

### Duplicate Notifications

**Problem**: Same notification appears multiple times

**Solutions**:
1. This is by design - duplicate detection uses 30-minute window
2. To change: edit `task_event_service.py` and `create_if_not_duplicate()` call
3. Or use `NotificationService.create()` instead of `create_if_not_duplicate()`

### Alerts Not Popping Up

**Problem**: Critical notifications don't show as popups

**Solutions**:
1. Ensure notification_type is exactly "critical"
2. Check that notification is marked `is_read=false`
3. Verify alertsContainer div exists in page
4. Check browser console for JavaScript errors

### Multiple Instances Running

**Problem**: Bell doesn't work on all pages / works only once

**Fixed by**: Updated initialization to check for existing instance and prevent duplicates

If you still have issues:
1. Check `window.notificationSystem` in browser console - should exist
2. If not, check for JavaScript errors preventing initialization
3. Try clearing browser storage: `localStorage.clear()` in console

## API Reference

### Create Test Notification
```
POST /notifications/test/create
Body: {
  "user_id": 1,
  "title": "Title",
  "message": "Message",
  "notification_type": "critical|warning|info|recommendation",
  "detail": "Optional detailed explanation"
}
```

### Get Unread Notifications
```
GET /notifications/unread?user_id=1
```

### Mark as Read
```
PUT /notifications/{id}/read
```

### Mark All as Read
```
PUT /notifications/read-all?user_id=1
```

### Get by Type
```
GET /notifications/?user_id=1&type=critical&page=1&per_page=20
```

## Key Fixes Applied

1. **Single Instance** - Only one NotificationSystem instance created globally
2. **Event Listener Cleanup** - Removed duplicate event listeners on re-init
3. **Error Handling** - Try-catch blocks around all DOM operations
4. **Read Status Persistence** - Immediately update local state before API call
5. **Alert Queue Management** - Track shown alerts to prevent duplicates
6. **localStorage Backup** - Persist shown alert IDs to survive page refresh
7. **Dropdown Rendering** - Clone and replace items to avoid listener conflicts

## Performance Tips

- Notifications refresh every 10 seconds (configurable in notification_ui.html)
- Change: `NOTIFICATION_CONFIG.updateInterval = 5000` for 5-second refresh
- Task intelligence caches for 5 minutes to reduce load
- Consider Redis cache for multi-worker deployments
