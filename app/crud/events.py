import uuid
import os
from sqlalchemy.orm import Session
from app.models.events import Event, Notification

UPLOAD_FOLDER = "app/static/uploads"

def create_event(db: Session, data, flyer_file):
    # Generate unique filename
    filename = f"{uuid.uuid4().hex}_{flyer_file.filename}"
    file_path = os.path.join(UPLOAD_FOLDER, filename)

    # Save image
    with open(file_path, "wb") as buffer:
        buffer.write(flyer_file.file.read())

    # Save to DB
    new_event = Event(
        event_name=data.event_name,
        state=data.state,
        venue=data.venue,
        date=data.date,
        time=data.time,
        dress_code=data.dress_code,
        event_description=data.event_description,
        event_flyer=filename,
    )

    db.add(new_event)
    db.commit()
    db.refresh(new_event)
    return new_event

def push_notification(db: Session, message: str, type_: str, entity_id: int = None, extra_data: dict = None):
    notification = Notification(
        message=message,
        type=type_,
        entity_id=entity_id,
        extra_data=extra_data or {}
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification
