from fastapi import APIRouter, Depends, UploadFile, File, Form, Query
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.deps.deps import get_db
from app.models.events import Event, Notification, Newsletter, Banner
from app.schemas.events import EventCreate, NotificationOut, NewsletterCreate, EventUpdateSchema, BannerOut, BannerUpdate
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
async def create_event(
    event_name: str = Form(...),
    state: str = Form(...),
    venue: str = Form(...),
    date: date = Form(...),
    time: str = Form(...),
    dress_code: str = Form(""),
    event_description: str = Form(""),
    is_featured: bool = Form(False),
    event_flyer: UploadFile = File(None),  # File upload
    db: Session = Depends(get_db),
    user: User = Depends(get_active_user)
):
    flyer_path = None
    if event_flyer:
        # Validate file type
        if not event_flyer.content_type.startswith('image/'):
            raise HTTPException(400, "File must be an image")
        
        # Generate unique filename
        file_extension = event_flyer.filename.split('.')[-1]
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        file_path = f"uploads/events/{unique_filename}"
        
        # Save file
        os.makedirs("uploads/events", exist_ok=True)
        with open(file_path, "wb") as buffer:
            content = await event_flyer.read()
            buffer.write(content)
        
        flyer_path = file_path

    new_event = Event(
        event_name=event_name,
        state=state,
        venue=venue,
        date=date,
        time=time,
        dress_code=dress_code,
        event_description=event_description,
        is_featured=is_featured,
        event_flyer=flyer_path  # Store file path
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
async def edit_event(
    event_id: int,
    event_name: Optional[str] = Form(None),
    state: Optional[str] = Form(None),
    venue: Optional[str] = Form(None),
    date: Optional[date] = Form(None),
    time: Optional[str] = Form(None),
    dress_code: Optional[str] = Form(None),
    event_description: Optional[str] = Form(None),
    is_featured: Optional[bool] = Form(None),
    event_flyer: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    user=Depends(get_active_user)
):
    # Find event by ID
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Update text fields if provided
    if event_name is not None:
        event.event_name = event_name
    if state is not None:
        event.state = state
    if venue is not None:
        event.venue = venue
    if date is not None:
        event.date = date
    if time is not None:
        event.time = time
    if dress_code is not None:
        event.dress_code = dress_code
    if event_description is not None:
        event.event_description = event_description
    if is_featured is not None:
        event.is_featured = is_featured

    # Handle flyer upload if provided
    if event_flyer:
        # Delete old flyer file if it exists
        if event.event_flyer:
            old_file_path = event.event_flyer.lstrip('/')
            if os.path.exists(old_file_path):
                os.remove(old_file_path)
        
        # Validate and save new flyer
        if not event_flyer.content_type.startswith('image/'):
            raise HTTPException(400, "File must be an image")
        
        file_extension = event_flyer.filename.split('.')[-1]
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        file_path = f"uploads/events/{unique_filename}"
        
        os.makedirs("uploads/events", exist_ok=True)
        with open(file_path, "wb") as buffer:
            content = await event_flyer.read()
            buffer.write(content)
        
        event.event_flyer = f"/uploads/events/{unique_filename}"

    db.commit()
    db.refresh(event)
    
    return {"message": "Event updated successfully", "event": event}


@router.put("/approve-event/{event_id}")
def approve_event(
    event_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_active_user)
):
    # Find event by ID
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Set is_featured to True
    event.is_featured = True
    db.commit()
    db.refresh(event)

    return {"message": f"Event '{event.event_name}' approved successfully", "event": event}

@router.put("/unapprove-event/{event_id}/unapprove")
def unapprove_event(event_id: int, db: Session = Depends(get_db), user=Depends(get_active_user)):
    # Find the event
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Set is_featured to False
    event.is_featured = False
    db.commit()
    db.refresh(event)

    return {"message": "Event unapproved successfully", "event": event}



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



































def check_approved_banner_limit(db: Session, exclude_id: Optional[int] = None):
    query = db.query(Banner).filter(Banner.is_approved == True)
    if exclude_id:
        query = query.filter(Banner.id != exclude_id)
    approved_count = query.count()
    return approved_count < 10

# Helper function to save uploaded file
async def save_banner_file(file: UploadFile) -> str:
    if not file.content_type.startswith('image/'):
        raise HTTPException(400, "File must be an image")
    
    file_extension = file.filename.split('.')[-1]
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = f"uploads/banners/{unique_filename}"
    
    os.makedirs("uploads/banners", exist_ok=True)
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    
    return f"/uploads/banners/{unique_filename}"

@router.post("/banners/create", response_model=BannerOut)
async def add_banner(
    name: str = Form(...),
    banner: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_active_user)
):
    # Save the banner image
    banner_path = await save_banner_file(banner)
    
    new_banner = Banner(
        name=name,
        banner_image=banner_path,
        is_approved=False  # Default to not approved
    )
    
    db.add(new_banner)
    db.commit()
    db.refresh(new_banner)

    push_notification(
        db,
        message=f"New banner '{new_banner.name}' created",
        type_="banner",  # Changed from "event" to "banner"
        entity_id=new_banner.id,
        extra_data={"name": new_banner.name}  # Added some useful data
    )
    
    return new_banner



@router.put("/banners/{banner_id}", response_model=BannerOut)
async def edit_banner(
    banner_id: int,
    name: Optional[str] = Form(None),
    banner: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_active_user)
):
    # Get existing banner
    existing_banner = db.query(Banner).filter(Banner.id == banner_id).first()
    if not existing_banner:
        raise HTTPException(status_code=404, detail="Banner not found")
    
    # Update name if provided
    if name:
        existing_banner.name = name
    
    # Update banner image if provided
    if banner:
        # Delete old file if it exists
        if existing_banner.banner_image:
            old_file_path = existing_banner.banner_image.lstrip('/')
            if os.path.exists(old_file_path):
                os.remove(old_file_path)
        
        # Save new file
        banner_path = await save_banner_file(banner)
        existing_banner.banner_image = banner_path
    
    db.commit()
    db.refresh(existing_banner)
    
    return existing_banner

@router.delete("/banners/{banner_id}")
def delete_banner(
    banner_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_active_user)
):
    banner = db.query(Banner).filter(Banner.id == banner_id).first()
    if not banner:
        raise HTTPException(status_code=404, detail="Banner not found")
    
    # Delete file if it exists
    if banner.banner_image:
        file_path = banner.banner_image.lstrip('/')
        if os.path.exists(file_path):
            os.remove(file_path)
    
    db.delete(banner)
    db.commit()
    
    return {"message": "Banner deleted successfully"}

@router.patch("/banners/{banner_id}/approve", response_model=BannerOut)
def approve_banner(
    banner_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_active_user)
):
    banner = db.query(Banner).filter(Banner.id == banner_id).first()
    if not banner:
        raise HTTPException(status_code=404, detail="Banner not found")
    
    if banner.is_approved:
        raise HTTPException(status_code=400, detail="Banner is already approved")
    
    # Check if we can approve more banners
    if not check_approved_banner_limit(db):
        raise HTTPException(
            status_code=400, 
            detail="Cannot approve more banners. Maximum of 10 approved banners allowed."
        )
    
    banner.is_approved = True
    db.commit()
    db.refresh(banner)
    
    return banner

@router.patch("/banners/{banner_id}/unapprove", response_model=BannerOut)
def unapprove_banner(
    banner_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_active_user)
):
    banner = db.query(Banner).filter(Banner.id == banner_id).first()
    if not banner:
        raise HTTPException(status_code=404, detail="Banner not found")
    
    if not banner.is_approved:
        raise HTTPException(status_code=400, detail="Banner is already unapproved")
    
    banner.is_approved = False
    db.commit()
    db.refresh(banner)
    
    return banner

@router.get("/banners", response_model=List[BannerOut])
def get_banners(
    approved_only: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Banner)
    
    if approved_only is not None:
        query = query.filter(Banner.is_approved == approved_only)
    
    query = query.order_by(Banner.created_at.desc())
    return query.all()

@router.get("/banners/{banner_id}", response_model=BannerOut)
def get_banner(
    banner_id: int,
    db: Session = Depends(get_db)
):
    banner = db.query(Banner).filter(Banner.id == banner_id).first()
    if not banner:
        raise HTTPException(status_code=404, detail="Banner not found")
    return banner