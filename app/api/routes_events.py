from fastapi import APIRouter, Depends, UploadFile, File, Form, Query
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.deps.deps import get_db
from app.models.events import Event, Notification, Newsletter
from app.schemas.events import EventCreate, NotificationOut, NewsletterCreate, EventUpdateSchema
from app.crud.events import push_notification
from app.schemas.events import EventOut
from typing import List, Optional
from app.crud.user import get_current_user
from app.utils.user_deactivated_handler import get_active_user
from app.models.user import User
import uuid
import os
from datetime import date

router = APIRouter()







@router.post("/events/create")
def create_event(
    event: EventCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_active_user)  # Require authenticated user here
):
    # Decode base64 image if provided
    flyer_binary = None
    if event.event_flyer:
        try:
            flyer_binary = base64.b64decode(event.event_flyer)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid base64 image")

    new_event = Event(
        event_name=event.event_name,
        state=event.state,
        venue=event.venue,
        date=event.date,
        time=event.time,
        dress_code=event.dress_code or '',
        event_description=event.event_description or '',
        is_featured=event.is_featured,
        event_flyer=flyer_binary or ''
    )

    db.add(new_event)
    db.commit()
    db.refresh(new_event)

    # Push notification
    push_notification(
        db,
        message=f"New event '{new_event.event_name}' created",
        type_="event",
        entity_id=new_event.id,
        extra_data={"state": new_event.state, "venue": new_event.venue}
    )

    return {"message": "Event created successfully", "event_id": new_event.id}




@router.get("/events", response_model=List[EventOut])
def get_events(
    state: Optional[str] = Query(None, description="Filter by state"),
    is_featured: Optional[bool] = Query(None, description="Filter by is_featured"),
    limit: Optional[int] = Query(None, description="Number of latest events to fetch"),
    db: Session = Depends(get_db)
):
    query = db.query(Event)

    # Filter by state if provided
    if state:
        query = query.filter(Event.state == state)

    # Filter by is_featured if provided
    if is_featured is not None:
        query = query.filter(Event.is_featured == is_featured)

    # Order by newest first
    query = query.order_by(Event.created_at.desc())

    # Apply limit if provided
    if limit:
        query = query.limit(limit)

    return query.all()



@router.get("/notifications", response_model=List[NotificationOut])
def get_notifications(
    status: Optional[str] = Query(None, description="Filter by status (unread/read)"),
    type_: Optional[str] = Query(None, description="Filter by notification type"),
    limit: Optional[int] = Query(None, description="Number of notifications to return"),
    db: Session = Depends(get_db)
):
    query = db.query(Notification)

    # Filter by status if provided
    if status:
        query = query.filter(Notification.status == status)

    # Filter by type if provided
    if type_:
        query = query.filter(Notification.type == type_)

    # Order by newest first
    query = query.order_by(Notification.created_at.desc())

    # Limit if provided
    if limit:
        query = query.limit(limit)

    return query.all()


@router.put("/deactivate-user/{user_id}")
def deactivate_user(user_id: int, db: Session = Depends(get_db), user=Depends(get_active_user)):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_deactivated:
        raise HTTPException(status_code=400, detail="User is already deactivated")

    user.is_deactivated = True
    db.commit()
    return {"message": f"User {user.email} has been deactivated"}


@router.put("/activate-user/{user_id}")
def activate_user(user_id: int, db: Session = Depends(get_db), user=Depends(get_active_user)):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.is_deactivated:
        raise HTTPException(status_code=400, detail="User is already active")

    user.is_deactivated = False
    db.commit()
    return {"message": f"User {user.email} has been activated"}



@router.post("/newsletter", status_code=201)
def add_to_newsletter(data: NewsletterCreate, db: Session = Depends(get_db)):
    # Check if email already exists
    existing_email = db.query(Newsletter).filter(Newsletter.email == data.email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already subscribed")

    # Create and save
    new_entry = Newsletter(email=data.email)
    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)

    return {"message": "Email added to newsletter list", "email": new_entry.email}




@router.put("/events/{event_id}")
def edit_event(
    event_id: int,
    event_data: EventUpdateSchema,
    db: Session = Depends(get_db),
    user=Depends(get_active_user)
):
    # Find event by ID
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Update fields dynamically
    for key, value in event_data.dict(exclude_unset=True).items():
        setattr(event, key, value)

    db.commit()
    db.refresh(event)
    return {"message": "Event updated successfully", "event": event}


# Delete Event
@router.delete("/events/{event_id}")
def delete_event(
    event_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_active_user)
):
    # Find event by ID
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    db.delete(event)
    db.commit()
    return {"message": "Event deleted successfully"}