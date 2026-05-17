#!/usr/bin/env python
"""Debug script to check notifications in the database."""
import sys
sys.path.insert(0, '.')

from app import create_app
from app.models.notification import Notification
from app.models.weekly_plan import WeeklyPlanEntry

app = create_app()
with app.app_context():
    print("\n=== CHANGE Notifications ===")
    notifs = Notification.query.filter_by(notification_type='change').order_by(Notification.created_at.desc()).limit(10).all()
    print(f"Total CHANGE notifications: {len(notifs)}\n")
    for n in notifs:
        detail_len = len(n.detail or "")
        print(f"ID {n.id} | {n.title}")
        print(f"  Read: {n.is_read} | Detail length: {detail_len}")
        print(f"  Created: {n.created_at}\n")
    
    print("\n=== WeeklyPlanEntry Climate Adjustments ===")
    entries = WeeklyPlanEntry.query.limit(5).all()
    print(f"Total WeeklyPlanEntries queried: {len(entries)}\n")
    for e in entries:
        print(f"Entry {e.id} (crop_id={e.crop_id}):")
        print(f"  climate_adjustments: {e.climate_adjustments[:100] if e.climate_adjustments else 'None'}...\n")
