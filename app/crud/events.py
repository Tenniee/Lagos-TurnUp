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
    """Create and save a notification to the database"""
    
    print(f"Push notification created: {message}")
    
    try:
        # Create the actual Notification database object
        notification = Notification(
            message=message,
            type=type_,
            entity_id=entity_id,
            extra_data=extra_data or {}
        )
        
        print(f"Notification object created")
        
        # Add to database session
        db.add(notification)
        print("Added to session")
        
        # Commit the transaction
        db.commit()
        print("Committed to database")
        
        # Refresh to get the ID and other auto-generated fields
        db.refresh(notification)
        print(f"Notification saved with ID: {notification.id}")
        
        return notification  # Return the SQLAlchemy object, not a dict!
        
    except Exception as e:
        print(f"Error creating notification: {e}")
        db.rollback()
        raise

        

def create_spot(db: Session, data, cover_image_file):
    # Generate unique filename
    filename = f"{uuid.uuid4().hex}_{cover_image_file.filename}"
    file_path = os.path.join(UPLOAD_FOLDER, filename)

    # Save image
    with open(file_path, "wb") as buffer:
        buffer.write(cover_image_file.file.read())

    # Save to DB
    new_spot = Spot(
        location_name=data.location_name,
        city=data.city,
        state=data.state,
        spot_type=data.spot_type,
        additional_info=data.additional_info,
        cover_image=filename,
    )

    db.add(new_spot)
    db.commit()
    db.refresh(new_spot)
    return new_spot





def edit_spot(db: Session, spot_id: int, data, cover_image_file=None):
    # Get existing spot
    spot = db.query(Spot).filter(Spot.id == spot_id).first()
    if not spot:
        return None
    
    # Handle image update if provided
    if cover_image_file:
        # Delete old image if it exists
        if spot.cover_image:
            old_file_path = os.path.join(UPLOAD_FOLDER, spot.cover_image)
            if os.path.exists(old_file_path):
                os.remove(old_file_path)
        
        # Save new image
        filename = f"{uuid.uuid4().hex}_{cover_image_file.filename}"
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        
        with open(file_path, "wb") as buffer:
            buffer.write(cover_image_file.file.read())
        
        spot.cover_image = filename
    
    # Update other fields
    spot.location_name = data.location_name
    spot.city = data.city
    spot.state = data.state
    spot.spot_type = data.spot_type
    spot.additional_info = data.additional_info

    db.commit()
    db.refresh(spot)
    return spot