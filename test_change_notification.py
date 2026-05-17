#!/usr/bin/env python
"""
Test script to trigger change notification manually and see what gets created.
"""
import sys
import json
sys.path.insert(0, '.')

from app import create_app
from app.services.domain_service.notification_service import NotificationService
from app.models.notification import Notification

app = create_app()
with app.app_context():
    user_id = 1
    
    print(f"\n{'='*60}")
    print(f"Testing change_summary notification for user {user_id}")
    print(f"{'='*60}\n")
    
    # Count notifications before
    before = Notification.query.filter_by(user_id=user_id).count()
    print(f"Notifications before: {before}")
    
    # Trigger the notification
    print(f"\nCalling generate_notifications with tag='change_summary'...")
    result = NotificationService().generate_notifications(user_id, tag="change_summary")
    print(f"Result: {result}")
    
    # Count notifications after
    after = Notification.query.filter_by(user_id=user_id).count()
    print(f"\nNotifications after: {after}")
    print(f"Created: {after - before} new notifications")
    
    # Show the change notifications
    print(f"\n{'='*60}")
    print(f"CHANGE Notifications:")
    print(f"{'='*60}")
    changes = Notification.query.filter_by(user_id=user_id, notification_type="change").order_by(Notification.created_at.desc()).all()
    for n in changes[:5]:
        print(f"\nID {n.id}: {n.title}")
        print(f"  Message: {n.message}")
        print(f"  Read: {n.is_read}")
        print(f"  Detail length: {len(n.detail or '')}")
        if n.detail:
            try:
                detail_json = json.loads(n.detail)
                print(f"  Detail keys: {list(detail_json.keys())}")
            except:
                print(f"  Detail (first 100 chars): {n.detail[:100]}...")
    
    print(f"\n{'='*60}")
    print(f"ALL unread critical/alert/change:")
    print(f"{'='*60}")
    criticals = Notification.query.filter_by(user_id=user_id, is_read=False).filter(
        Notification.notification_type.in_(["critical", "alert", "change"])
    ).all()
    for n in criticals[:5]:
        print(f"  {n.notification_type:10} | {n.title[:40]}")
