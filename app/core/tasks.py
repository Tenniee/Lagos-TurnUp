# tasks.py
from datetime import datetime, timezone
from app.core.database import SessionLocal
from app.models.events import Event

def unfeature_expired_events():
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        updated = db.query(Event).filter(
            Event.featured_until <= now,
            Event.is_featured == True
        ).update({"is_featured": False, "featuring_timeline": None})
        db.commit()
        print(f"[Scheduler] Unfeatured {updated} events")
    finally:
        db.close()

def delete_old_events():
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        deleted = db.query(Event).filter(Event.delete_after <= now).delete()
        db.commit()
        print(f"[Scheduler] Deleted {deleted} events")
    finally:
        db.close()