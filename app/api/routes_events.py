from fastapi import APIRouter, Depends, UploadFile, File, Form, Query
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from app.deps.deps import get_db
from app.models.events import Event, Notification, Newsletter, Banner, Spot
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


import logging
logger = logging.getLogger(__name__)

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
    event_flyer: UploadFile = File(None),
    
    # Featured request fields
    featured_requested: bool = Form(False),
    contact_method: str = Form(""),  # email, phone, whatsapp
    contact_link: str = Form(""),
    
    db: Session = Depends(get_db),
    user: User = Depends(get_active_user)
):
    # Validate contact method if featured is requested
    if featured_requested:
        valid_methods = ["email", "phone", "whatsapp"]
        if contact_method not in valid_methods:
            raise HTTPException(400, f"Invalid contact method. Must be one of: {', '.join(valid_methods)}")
        if not contact_link:
            raise HTTPException(400, "Contact link is required when requesting featured event")

    flyer_filename = None
    flyer_url = None
    
    if event_flyer:
        # Validate file type
        if not event_flyer.content_type.startswith('image/'):
            raise HTTPException(400, "File must be an image")
        
        # Validate file size (optional - add reasonable limit)
        content = await event_flyer.read()
        if len(content) > 5 * 1024 * 1024:  # 5MB limit
            raise HTTPException(400, "File size too large. Maximum 5MB allowed.")
        
        # Generate unique filename
        file_extension = event_flyer.filename.split('.')[-1].lower()
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        file_path = f"uploads/events/{unique_filename}"
        
        # Save file
        os.makedirs("uploads/events", exist_ok=True)
        try:
            with open(file_path, "wb") as buffer:
                buffer.write(content)
            
            # Store only filename in database
            flyer_filename = unique_filename
            # Create URL for frontend access
            flyer_url = f"/static/events/{unique_filename}"
            
        except Exception as e:
            raise HTTPException(500, f"Failed to save file: {str(e)}")

    new_event = Event(
        event_name=event_name,
        state=state,
        venue=venue,
        date=date,
        time=time,
        dress_code=dress_code,
        event_description=event_description,
        event_flyer=flyer_filename,  # Store filename only
        is_featured=False,  # Always False initially
        pending=True,
        
        # Featured request data
        featured_requested=featured_requested,
        contact_method=contact_method if featured_requested else None,
        contact_link=contact_link if featured_requested else None,
    )

    try:
        db.add(new_event)
        db.commit()
        db.refresh(new_event)
    except Exception as e:
        db.rollback()
        # Clean up uploaded file if database operation fails
        if flyer_filename and os.path.exists(f"uploads/events/{flyer_filename}"):
            os.remove(f"uploads/events/{flyer_filename}")
        raise HTTPException(500, f"Database error: {str(e)}")

    # Smart notification based on event type
    if featured_requested:
        push_notification(
            db,
            message=f"🌟 New FEATURED event request: '{new_event.event_name}' - Contact via {contact_method}",
            type_="featured_event",
            entity_id=new_event.id,
            extra_data={
                "state": new_event.state, 
                "venue": new_event.venue,
                "contact_method": contact_method,
                "contact_link": contact_link,
                "featured": True
            }
        )
    else:
        push_notification(
            db,
            message=f"New event '{new_event.event_name}' created",
            type_="event",
            entity_id=new_event.id,
            extra_data={
                "state": new_event.state, 
                "venue": new_event.venue,
                "featured": False
            }
        )

    return {
        "message": "Event created successfully", 
        "event_id": new_event.id, 
        "featured_requested": featured_requested,
        "image_url": flyer_url  # Include accessible URL
    }






@router.get("/events", response_model=List[EventOut])
def get_events(
    id: Optional[int] = Query(None, description="Filter by event ID"),
    state: Optional[str] = Query(None, description="Filter by state"),
    is_featured: Optional[bool] = Query(None, description="Filter by is_featured"),
    pending: Optional[bool] = Query(None, description="Filter by pending status"),
    limit: Optional[int] = Query(None, description="Number of latest events to fetch"),
    db: Session = Depends(get_db)
):
    query = db.query(Event)

    # Filter by ID if provided
    if id is not None:
        query = query.filter(Event.id == id)

    # Filter by state if provided
    if state:
        query = query.filter(Event.state == state)

    # Filter by is_featured if provided
    if is_featured is not None:
        query = query.filter(Event.is_featured == is_featured)

    # Filter by pending if provided
    if pending is not None:
        query = query.filter(Event.pending == pending)

    # Order by newest first
    query = query.order_by(Event.created_at.desc())

    # Apply limit if provided
    if limit:
        query = query.limit(limit)

    return query.all()








@router.put("/events/{event_id}/approve-featured") 
async def approve_featured_event(
    event_id: int, 
    db: Session = Depends(get_db), 
    user: User = Depends(get_active_user)
): 
    try:
        event = db.query(Event).filter(Event.id == event_id).first() 
        if not event: 
            raise HTTPException(404, "Event not found") 
         
        if not event.featured_requested: 
            raise HTTPException(400, "Event was not requested to be featured") 
         
        event.is_featured = True 
        
        # Create notification in same transaction
        notification = push_notification(
            db, 
            message=f"🎉 Event '{event.event_name}' is now FEATURED!", 
            type_="event_featured", 
            entity_id=event.id, 
            extra_data={
                "event_name": event.event_name, 
                "state": event.state, 
                "venue": event.venue 
            }
        )
        
        # Commit both changes together
        db.commit() 
        db.refresh(event)
        
        return {"message": f"Event '{event.event_name}' is now featured!", "is_featured": True}
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to approve featured event: {e}")
        raise




# Get featured requests for admin
@router.get("/admin/featured-requests")
async def get_featured_requests(
    db: Session = Depends(get_db),
    user: User = Depends(get_active_user)
):
    # Get events that requested featured but aren't featured yet
    events = db.query(Event).filter(
        Event.featured_requested == True,
        Event.is_featured == False
    ).all()
    return events












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
    
    try:
        db.add(new_entry)
        db.commit()
        db.refresh(new_entry)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    # Extract email domain and user info for analytics
    email_domain = data.email.split('@')[1] if '@' in data.email else 'unknown'
    email_username = data.email.split('@')[0] if '@' in data.email else data.email
    
    # Determine engagement level based on email domain
    high_engagement_domains = ['gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com']
    business_domains = ['company.com', 'corp.com', 'inc.com', 'ltd.com']  # You can customize this
    
    engagement_level = "high"
    if email_domain in high_engagement_domains:
        engagement_level = "high"
    elif any(keyword in email_domain for keyword in business_domains):
        engagement_level = "business"
    else:
        engagement_level = "medium"

    # Smart push notification for newsletter signup
    push_notification(
        db,
        message=f"📧 New newsletter subscription: {data.email}",
        type_="newsletter_signup",
        entity_id=new_entry.id,
        extra_data={
            "email": data.email,
            "email_domain": email_domain,
            "email_username": email_username,
            "engagement_level": engagement_level,
            "subscription_source": "api",  # You can track different sources
            "category": "newsletter",
            "action": "newsletter_signup",
            "is_new_subscriber": True,
            "subscriber_id": new_entry.id,
            "domain_type": "consumer" if email_domain in high_engagement_domains else "business" if any(keyword in email_domain for keyword in business_domains) else "other"
        }
    )

    return {
        "message": "Email added to newsletter list", 
        "email": new_entry.email,
        "subscriber_id": new_entry.id,
        "engagement_level": engagement_level
    }





@router.get("/newsletter")
def get_newsletter_subscriptions(
    limit: Optional[int] = Query(None, ge=1, description="Limit number of results"),
    offset: Optional[int] = Query(0, ge=0, description="Skip number of records"),
    email_filter: Optional[str] = Query(None, description="Filter by email (partial match)"),
    domain_filter: Optional[str] = Query(None, description="Filter by email domain"),
    sort_by: Optional[str] = Query("newest", description="Sort by: newest, oldest, email"),
    db: Session = Depends(get_db)
):
    """
    Get all newsletter subscriptions with filtering and pagination options
    
    Args:
        limit: Maximum number of subscriptions to return
        offset: Number of subscriptions to skip
        email_filter: Filter by email containing this text
        domain_filter: Filter by specific email domain
        sort_by: Sort order (newest, oldest, email)
        db: Database session
    
    Returns:
        Dictionary with subscriptions list and metadata
    """
    
    # Base query
    query = db.query(Newsletter)
    
    # Apply filters
    if email_filter:
        query = query.filter(Newsletter.email.ilike(f"%{email_filter}%"))
    
    if domain_filter:
        query = query.filter(Newsletter.email.ilike(f"%@{domain_filter}%"))
    
    # Apply sorting
    if sort_by == "newest":
        query = query.order_by(desc(Newsletter.id))
    elif sort_by == "oldest":
        query = query.order_by(Newsletter.id)
    elif sort_by == "email":
        query = query.order_by(Newsletter.email)
    else:
        # Default to newest
        query = query.order_by(desc(Newsletter.id))
    
    # Get total count before pagination
    total_count = query.count()
    
    # Apply pagination
    if offset:
        query = query.offset(offset)
    if limit:
        query = query.limit(limit)
    
    # Execute query
    subscriptions = query.all()
    
    # Extract email domains for analytics
    email_domains = {}
    engagement_stats = {"high": 0, "business": 0, "medium": 0}
    
    high_engagement_domains = ['gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com']
    business_domains = ['company.com', 'corp.com', 'inc.com', 'ltd.com']
    
    for subscription in subscriptions:
        # Extract domain
        if '@' in subscription.email:
            domain = subscription.email.split('@')[1]
            email_domains[domain] = email_domains.get(domain, 0) + 1
            
            # Calculate engagement level
            if domain in high_engagement_domains:
                engagement_stats["high"] += 1
            elif any(keyword in domain for keyword in business_domains):
                engagement_stats["business"] += 1
            else:
                engagement_stats["medium"] += 1
    
    # Prepare response
    response_data = {
        "subscriptions": [
            {
                "id": sub.id,
                "email": sub.email,
                "domain": sub.email.split('@')[1] if '@' in sub.email else 'unknown',
                "engagement_level": (
                    "high" if '@' in sub.email and sub.email.split('@')[1] in high_engagement_domains
                    else "business" if '@' in sub.email and any(keyword in sub.email.split('@')[1] for keyword in business_domains)
                    else "medium"
                )
            }
            for sub in subscriptions
        ],
        "metadata": {
            "total_count": total_count,
            "returned_count": len(subscriptions),
            "offset": offset,
            "limit": limit,
            "has_more": total_count > (offset + len(subscriptions)) if limit else False
        },
        "analytics": {
            "total_subscribers": total_count,
            "top_domains": dict(sorted(email_domains.items(), key=lambda x: x[1], reverse=True)[:10]),
            "engagement_breakdown": engagement_stats,
            "domain_diversity": len(email_domains)
        }
    }
    return response_data





@router.get("/newsletter/{subscription_id}")
def get_newsletter_subscription_by_id(
    subscription_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific newsletter subscription by ID
    
    Args:
        subscription_id: ID of the newsletter subscription
        db: Database session
    
    Returns:
        Newsletter subscription details
    """
    
    subscription = db.query(Newsletter).filter(Newsletter.id == subscription_id).first()
    
    if not subscription:
        raise HTTPException(status_code=404, detail=f"Newsletter subscription with ID {subscription_id} not found")
    
    # Calculate engagement level
    high_engagement_domains = ['gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com']
    business_domains = ['company.com', 'corp.com', 'inc.com', 'ltd.com']
    
    domain = subscription.email.split('@')[1] if '@' in subscription.email else 'unknown'
    
    engagement_level = (
        "high" if domain in high_engagement_domains
        else "business" if any(keyword in domain for keyword in business_domains)
        else "medium"
    )
    
    return {
        "id": subscription.id,
        "email": subscription.email,
        "domain": domain,
        "engagement_level": engagement_level,
        "email_username": subscription.email.split('@')[0] if '@' in subscription.email else subscription.email
    }






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
    
    # Featured request fields
    featured_requested: Optional[bool] = Form(None),
    contact_method: Optional[str] = Form(None),  # email, phone, whatsapp
    contact_link: Optional[str] = Form(None),
    
    event_flyer: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    user=Depends(get_active_user)
):
    # Find event by ID
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Store original values for comparison
    original_featured = event.is_featured
    original_featured_requested = event.featured_requested
    original_name = event.event_name

    # Validate featured request fields if being updated
    if featured_requested is not None and featured_requested:
        # If they're requesting featured, validate the contact info
        final_contact_method = contact_method if contact_method is not None else event.contact_method
        final_contact_link = contact_link if contact_link is not None else event.contact_link
        
        valid_methods = ["email", "phone", "whatsapp"]
        if final_contact_method not in valid_methods:
            raise HTTPException(400, f"Invalid contact method. Must be one of: {', '.join(valid_methods)}")
        if not final_contact_link:
            raise HTTPException(400, "Contact link is required when requesting featured event")

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
    
    # Update featured request fields if provided
    if featured_requested is not None:
        event.featured_requested = featured_requested
        # If they're no longer requesting featured, clear the contact info
        if not featured_requested:
            event.contact_method = None
            event.contact_link = None
    
    if contact_method is not None:
        event.contact_method = contact_method if event.featured_requested else None
    
    if contact_link is not None:
        event.contact_link = contact_link if event.featured_requested else None

    # Handle flyer upload if provided
    flyer_updated = False
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
        flyer_updated = True

    db.commit()
    db.refresh(event)
    
    # Smart notification system based on what changed
    notification_sent = False
    
    # Priority 1: Featured status changes (most important)
    if is_featured is not None and is_featured != original_featured:
        if is_featured:
            push_notification(
                db,
                message=f"🌟 Event '{event.event_name}' has been FEATURED!",
                type_="event_featured",
                entity_id=event.id,
                extra_data={
                    "state": event.state,
                    "venue": event.venue,
                    "featured": True,
                    "status_change": "featured"
                }
            )
        else:
            push_notification(
                db,
                message=f"Event '{event.event_name}' is no longer featured",
                type_="event_unfeatured", 
                entity_id=event.id,
                extra_data={
                    "state": event.state,
                    "venue": event.venue,
                    "featured": False,
                    "status_change": "unfeatured"
                }
            )
        notification_sent = True
    
    # Priority 2: New featured request
    elif featured_requested is not None and featured_requested and not original_featured_requested:
        push_notification(
            db,
            message=f"🌟 New FEATURED request for updated event: '{event.event_name}' - Contact via {event.contact_method}",
            type_="featured_event_request",
            entity_id=event.id,
            extra_data={
                "state": event.state,
                "venue": event.venue,
                "contact_method": event.contact_method,
                "contact_link": event.contact_link,
                "featured_requested": True,
                "action": "edit_with_featured_request"
            }
        )
        notification_sent = True
    
    # Priority 3: Major content changes (if no featured status change)
    elif not notification_sent:
        major_changes = []
        
        # Check for significant changes
        if event_name is not None and event_name != original_name:
            major_changes.append("name")
        if date is not None:
            major_changes.append("date")
        if time is not None:
            major_changes.append("time")
        if venue is not None:
            major_changes.append("venue")
        if state is not None:
            major_changes.append("location")
        if flyer_updated:
            major_changes.append("flyer")
        
        if major_changes:
            # Create a descriptive message based on what changed
            if len(major_changes) == 1:
                change_text = major_changes[0]
            elif len(major_changes) == 2:
                change_text = f"{major_changes[0]} and {major_changes[1]}"
            else:
                change_text = f"{', '.join(major_changes[:-1])}, and {major_changes[-1]}"
            
            push_notification(
                db,
                message=f"📝 Event '{event.event_name}' updated - {change_text} changed",
                type_="event_updated",
                entity_id=event.id,
                extra_data={
                    "state": event.state,
                    "venue": event.venue,
                    "featured": event.is_featured,
                    "changes": major_changes,
                    "action": "major_update"
                }
            )
            notification_sent = True
        
        # Minor changes notification (if no major changes detected)
        elif not notification_sent:
            push_notification(
                db,
                message=f"📝 Event '{event.event_name}' details updated",
                type_="event_minor_update",
                entity_id=event.id,
                extra_data={
                    "state": event.state,
                    "venue": event.venue,
                    "featured": event.is_featured,
                    "action": "minor_update"
                }
            )
    
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

    # Store original state for smart notification logic
    was_featured = event.is_featured
    was_pending = getattr(event, 'pending', False)
    had_featured_request = event.featured_requested if hasattr(event, 'featured_requested') else False

    # Set is_featured to True and clear pending status if it exists
    event.is_featured = True
    if hasattr(event, 'pending'):
        event.pending = False
    if hasattr(event, 'featured_requested'):
        event.featured_requested = False  # Clear request since it's been processed
    
    db.commit()
    db.refresh(event)

    # Smart notification based on the event's previous state
    if had_featured_request and not was_featured:
        # Event had requested featured status - this is an approval
        push_notification(
            db,
            message=f"🎉 APPROVED! Event '{event.event_name}' featured request accepted by admin!",
            type_="event_featured_request_approved",
            entity_id=event.id,
            extra_data={
                "event_name": event.event_name,
                "state": event.state,
                "venue": event.venue,
                "date": str(event.date),
                "time": event.time,
                "featured": True,
                "admin_action": True,
                "approved_by": getattr(user, 'id', 'admin'),
                "action": "featured_request_approved",
                "was_requested": True,
                "contact_method": getattr(event, 'contact_method', None),
                "contact_link": getattr(event, 'contact_link', None)
            }
        )
    elif was_pending and not was_featured:
        # Event was pending approval - general event approval with featured status
        push_notification(
            db,
            message=f"✅ Event '{event.event_name}' APPROVED and FEATURED by admin!",
            type_="event_approved_and_featured",
            entity_id=event.id,
            extra_data={
                "event_name": event.event_name,
                "state": event.state,
                "venue": event.venue,
                "date": str(event.date),
                "time": event.time,
                "featured": True,
                "admin_action": True,
                "approved_by": getattr(user, 'id', 'admin'),
                "action": "approved_and_featured",
                "was_pending": True
            }
        )
    elif not was_featured:
        # Event wasn't featured before - admin is promoting it to featured
        push_notification(
            db,
            message=f"🌟 Event '{event.event_name}' promoted to FEATURED by admin!",
            type_="event_promoted_featured",
            entity_id=event.id,
            extra_data={
                "event_name": event.event_name,
                "state": event.state,
                "venue": event.venue,
                "date": str(event.date),
                "time": event.time,
                "featured": True,
                "admin_action": True,
                "approved_by": getattr(user, 'id', 'admin'),
                "action": "promoted_to_featured",
                "was_already_live": True
            }
        )
    else:
        # Event was already featured - just a status confirmation
        push_notification(
            db,
            message=f"✅ Event '{event.event_name}' featured status confirmed by admin",
            type_="event_featured_confirmed",
            entity_id=event.id,
            extra_data={
                "event_name": event.event_name,
                "state": event.state,
                "venue": event.venue,
                "featured": True,
                "admin_action": True,
                "approved_by": getattr(user, 'id', 'admin'),
                "action": "featured_status_confirmed",
                "was_already_featured": True
            }
        )

    return {
        "message": f"Event '{event.event_name}' approved successfully", 
        "event": event,
        "featured_status": "approved"
    }





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

    # Store event data for notification before deletion
    event_name = event.event_name
    event_state = event.state
    event_venue = event.venue
    event_date = str(event.date) if event.date else None
    event_time = event.time
    was_featured = event.is_featured
    was_pending = getattr(event, 'pending', False)
    had_featured_request = getattr(event, 'featured_requested', False)
    contact_method = getattr(event, 'contact_method', None)
    
    # Clean up event flyer file if it exists
    if hasattr(event, 'event_flyer') and event.event_flyer:
        flyer_path = event.event_flyer.lstrip('/')
        if os.path.exists(flyer_path):
            try:
                os.remove(flyer_path)
            except Exception as e:
                # Log error but don't fail deletion
                print(f"Failed to delete flyer file: {e}")

    # Delete the event
    db.delete(event)
    db.commit()

    # Smart notification based on what type of event was deleted
    if was_featured:
        # Featured event deleted - high impact
        push_notification(
            db,
            message=f"🗑️ FEATURED event '{event_name}' has been DELETED by admin!",
            type_="featured_event_deleted",
            entity_id=event_id,  # Keep the ID for reference even though event is gone
            extra_data={
                "event_name": event_name,
                "state": event_state,
                "venue": event_venue,
                "date": event_date,
                "time": event_time,
                "was_featured": True,
                "admin_action": True,
                "deleted_by": getattr(user, 'id', 'admin'),
                "action": "featured_event_deleted",
                "high_impact": True,
                "contact_method": contact_method
            }
        )
    elif had_featured_request:
        # Event with pending featured request deleted
        push_notification(
            db,
            message=f"🗑️ Event '{event_name}' with FEATURED REQUEST has been deleted by admin",
            type_="featured_request_event_deleted",
            entity_id=event_id,
            extra_data={
                "event_name": event_name,
                "state": event_state,
                "venue": event_venue,
                "date": event_date,
                "time": event_time,
                "had_featured_request": True,
                "admin_action": True,
                "deleted_by": getattr(user, 'id', 'admin'),
                "action": "featured_request_deleted",
                "contact_method": contact_method
            }
        )
    elif was_pending:
        # Pending event deleted
        push_notification(
            db,
            message=f"🗑️ Pending event '{event_name}' deleted by admin",
            type_="pending_event_deleted",
            entity_id=event_id,
            extra_data={
                "event_name": event_name,
                "state": event_state,
                "venue": event_venue,
                "date": event_date,
                "time": event_time,
                "was_pending": True,
                "admin_action": True,
                "deleted_by": getattr(user, 'id', 'admin'),
                "action": "pending_event_deleted"
            }
        )
    else:
        # Regular event deleted
        push_notification(
            db,
            message=f"🗑️ Event '{event_name}' deleted by admin",
            type_="event_deleted",
            entity_id=event_id,
            extra_data={
                "event_name": event_name,
                "state": event_state,
                "venue": event_venue,
                "date": event_date,
                "time": event_time,
                "admin_action": True,
                "deleted_by": getattr(user, 'id', 'admin'),
                "action": "event_deleted"
            }
        )

    return {
        "message": "Event deleted successfully",
        "deleted_event": event_name,
        "was_featured": was_featured
    }


































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
    banner_link: str = Form(""),  # Optional banner link
    banner: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_active_user)
):
    # Validate banner file
    if not banner.content_type.startswith('image/'):
        raise HTTPException(400, "File must be an image")
    
    # Validate file size (reasonable limit for banners)
    content = await banner.read()
    if len(content) > 10 * 1024 * 1024:  # 10MB limit for banners
        raise HTTPException(400, "Banner file too large. Maximum 10MB allowed.")
    
    # Reset file pointer for save_banner_file function
    banner.file.seek(0)
    
    # Save the banner image
    banner_path = await save_banner_file(banner)
    
    new_banner = Banner(
        name=name,
        banner_image=banner_path,
        banner_link=banner_link if banner_link else None,
        is_approved=False  # Default to not approved
    )
    
    try:
        db.add(new_banner)
        db.commit()
        db.refresh(new_banner)
    except Exception as e:
        # Clean up uploaded file if database operation fails
        if banner_path and os.path.exists(banner_path):
            os.remove(banner_path)
        raise HTTPException(500, f"Database error: {str(e)}")

    # Enhanced smart notification based on banner characteristics
    has_link = bool(banner_link and banner_link.strip())
    file_size_mb = round(len(content) / (1024 * 1024), 2)
    
    if has_link:
        # Banner with link - likely promotional/commercial
        push_notification(
            db,
            message=f"🎨 New PROMOTIONAL banner '{new_banner.name}' created - pending approval",
            type_="promotional_banner_created",
            entity_id=new_banner.id,
            extra_data={
                "name": new_banner.name,
                "has_link": True,
                "banner_link": new_banner.banner_link,
                "file_size_mb": file_size_mb,
                "is_approved": False,
                "created_by": getattr(user, 'id', 'user'),
                "banner_type": "promotional",
                "action": "banner_created_with_link",
                "requires_approval": True
            }
        )
    else:
        # Regular banner without link
        push_notification(
            db,
            message=f"🎨 New banner '{new_banner.name}' created - pending approval",
            type_="banner_created",
            entity_id=new_banner.id,
            extra_data={
                "name": new_banner.name,
                "has_link": False,
                "file_size_mb": file_size_mb,
                "is_approved": False,
                "created_by": getattr(user, 'id', 'user'),
                "banner_type": "standard",
                "action": "banner_created",
                "requires_approval": True
            }
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
    
    # Store original values for comparison
    original_name = existing_banner.name
    original_image_path = existing_banner.banner_image
    has_link = bool(existing_banner.banner_link)
    is_approved = getattr(existing_banner, 'is_approved', False)
    
    # Track what's being changed
    changes_made = []
    file_size_mb = None
    
    # Update name if provided
    if name and name != original_name:
        existing_banner.name = name
        changes_made.append("name")
    
    # Update banner image if provided
    if banner:
        # Validate new banner file
        if not banner.content_type.startswith('image/'):
            raise HTTPException(400, "File must be an image")
        
        # Check file size
        content = await banner.read()
        if len(content) > 10 * 1024 * 1024:  # 10MB limit
            raise HTTPException(400, "Banner file too large. Maximum 10MB allowed.")
        
        file_size_mb = round(len(content) / (1024 * 1024), 2)
        
        # Reset file pointer for save function
        banner.file.seek(0)
        
        # Delete old file if it exists
        if existing_banner.banner_image:
            old_file_path = existing_banner.banner_image.lstrip('/')
            if os.path.exists(old_file_path):
                try:
                    os.remove(old_file_path)
                except Exception as e:
                    print(f"Failed to delete old banner file: {e}")
        
        # Save new file
        try:
            banner_path = await save_banner_file(banner)
            existing_banner.banner_image = banner_path
            changes_made.append("image")
        except Exception as e:
            raise HTTPException(500, f"Failed to save banner file: {str(e)}")
    
    # Only commit and notify if changes were made
    if changes_made:
        try:
            db.commit()
            db.refresh(existing_banner)
        except Exception as e:
            # Clean up new file if database operation fails
            if banner and 'banner_path' in locals() and os.path.exists(banner_path):
                os.remove(banner_path)
            raise HTTPException(500, f"Database error: {str(e)}")
        
        # Smart notification based on what changed and banner status
        if len(changes_made) == 1:
            change_text = changes_made[0]
        elif len(changes_made) == 2:
            change_text = f"{changes_made[0]} and {changes_made[1]}"
        else:
            change_text = f"{', '.join(changes_made[:-1])}, and {changes_made[-1]}"
        
        # Different notifications based on banner type and approval status
        if has_link and is_approved:
            # Approved promotional banner edited - high impact
            push_notification(
                db,
                message=f"🎨 LIVE promotional banner '{existing_banner.name}' updated - {change_text} changed",
                type_="live_promotional_banner_updated",
                entity_id=existing_banner.id,
                extra_data={
                    "name": existing_banner.name,
                    "original_name": original_name,
                    "changes": changes_made,
                    "has_link": True,
                    "banner_link": existing_banner.banner_link,
                    "is_approved": True,
                    "file_size_mb": file_size_mb,
                    "updated_by": getattr(user, 'id', 'user'),
                    "banner_type": "promotional",
                    "status": "live",
                    "action": "live_banner_updated",
                    "high_impact": True
                }
            )
        elif is_approved:
            # Approved regular banner edited
            push_notification(
                db,
                message=f"🎨 LIVE banner '{existing_banner.name}' updated - {change_text} changed",
                type_="live_banner_updated",
                entity_id=existing_banner.id,
                extra_data={
                    "name": existing_banner.name,
                    "original_name": original_name,
                    "changes": changes_made,
                    "has_link": has_link,
                    "is_approved": True,
                    "file_size_mb": file_size_mb,
                    "updated_by": getattr(user, 'id', 'user'),
                    "banner_type": "standard",
                    "status": "live",
                    "action": "live_banner_updated"
                }
            )
        elif has_link:
            # Pending promotional banner edited
            push_notification(
                db,
                message=f"🎨 Promotional banner '{existing_banner.name}' updated - {change_text} changed (pending approval)",
                type_="pending_promotional_banner_updated",
                entity_id=existing_banner.id,
                extra_data={
                    "name": existing_banner.name,
                    "original_name": original_name,
                    "changes": changes_made,
                    "has_link": True,
                    "banner_link": existing_banner.banner_link,
                    "is_approved": False,
                    "file_size_mb": file_size_mb,
                    "updated_by": getattr(user, 'id', 'user'),
                    "banner_type": "promotional",
                    "status": "pending",
                    "action": "pending_banner_updated"
                }
            )
        else:
            # Pending regular banner edited
            push_notification(
                db,
                message=f"🎨 Banner '{existing_banner.name}' updated - {change_text} changed (pending approval)",
                type_="pending_banner_updated",
                entity_id=existing_banner.id,
                extra_data={
                    "name": existing_banner.name,
                    "original_name": original_name,
                    "changes": changes_made,
                    "has_link": has_link,
                    "is_approved": False,
                    "file_size_mb": file_size_mb,
                    "updated_by": getattr(user, 'id', 'user'),
                    "banner_type": "standard",
                    "status": "pending",
                    "action": "pending_banner_updated"
                }
            )
    
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






@router.delete("/banners/{banner_id}")
def delete_banner(
    banner_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_active_user)
):
    banner = db.query(Banner).filter(Banner.id == banner_id).first()
    if not banner:
        raise HTTPException(status_code=404, detail="Banner not found")
    
    # Store banner data for notification before deletion
    banner_name = banner.name
    banner_image_path = banner.banner_image
    has_link = bool(banner.banner_link)
    banner_link = banner.banner_link
    is_approved = getattr(banner, 'is_approved', False)
    
    # Calculate file size if file exists
    file_size_mb = None
    if banner_image_path:
        file_path = banner_image_path.lstrip('/')
        if os.path.exists(file_path):
            try:
                file_size_mb = round(os.path.getsize(file_path) / (1024 * 1024), 2)
            except Exception:
                file_size_mb = None
    
    # Delete file if it exists
    if banner.banner_image:
        file_path = banner.banner_image.lstrip('/')
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                # Log error but don't fail deletion
                print(f"Failed to delete banner file: {e}")
    
    # Delete the banner from database
    db.delete(banner)
    db.commit()
    
    # Smart notification based on banner type and approval status
    if is_approved and has_link:
        # Live promotional banner deleted - HIGHEST IMPACT
        push_notification(
            db,
            message=f"🗑️ LIVE PROMOTIONAL banner '{banner_name}' has been DELETED by admin!",
            type_="live_promotional_banner_deleted",
            entity_id=banner_id,  # Keep ID for reference even though banner is gone
            extra_data={
                "banner_name": banner_name,
                "had_link": True,
                "banner_link": banner_link,
                "was_approved": True,
                "file_size_mb": file_size_mb,
                "admin_action": True,
                "deleted_by": getattr(user, 'id', 'admin'),
                "banner_type": "promotional",
                "status": "was_live",
                "action": "live_promotional_deleted",
                "impact_level": "critical"
            }
        )
    elif is_approved:
        # Live standard banner deleted - HIGH IMPACT
        push_notification(
            db,
            message=f"🗑️ LIVE banner '{banner_name}' has been DELETED by admin!",
            type_="live_banner_deleted",
            entity_id=banner_id,
            extra_data={
                "banner_name": banner_name,
                "had_link": has_link,
                "was_approved": True,
                "file_size_mb": file_size_mb,
                "admin_action": True,
                "deleted_by": getattr(user, 'id', 'admin'),
                "banner_type": "standard",
                "status": "was_live",
                "action": "live_banner_deleted",
                "impact_level": "high"
            }
        )
    elif has_link:
        # Pending promotional banner deleted - MEDIUM IMPACT
        push_notification(
            db,
            message=f"🗑️ Pending PROMOTIONAL banner '{banner_name}' deleted by admin",
            type_="pending_promotional_banner_deleted",
            entity_id=banner_id,
            extra_data={
                "banner_name": banner_name,
                "had_link": True,
                "banner_link": banner_link,
                "was_approved": False,
                "file_size_mb": file_size_mb,
                "admin_action": True,
                "deleted_by": getattr(user, 'id', 'admin'),
                "banner_type": "promotional",
                "status": "was_pending",
                "action": "pending_promotional_deleted",
                "impact_level": "medium"
            }
        )
    else:
        # Pending standard banner deleted - LOW IMPACT
        push_notification(
            db,
            message=f"🗑️ Pending banner '{banner_name}' deleted by admin",
            type_="pending_banner_deleted",
            entity_id=banner_id,
            extra_data={
                "banner_name": banner_name,
                "had_link": has_link,
                "was_approved": False,
                "file_size_mb": file_size_mb,
                "admin_action": True,
                "deleted_by": getattr(user, 'id', 'admin'),
                "banner_type": "standard",
                "status": "was_pending",
                "action": "pending_banner_deleted",
                "impact_level": "low"
            }
        )
    
    return {
        "message": "Banner deleted successfully",
        "deleted_banner": banner_name,
        "was_approved": is_approved,
        "had_link": has_link
    }








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
    
    # Store banner data for notification context
    banner_name = banner.name
    has_link = bool(banner.banner_link)
    banner_link = banner.banner_link
    
    # Calculate file size if possible
    file_size_mb = None
    if banner.banner_image:
        file_path = banner.banner_image.lstrip('/')
        if os.path.exists(file_path):
            try:
                file_size_mb = round(os.path.getsize(file_path) / (1024 * 1024), 2)
            except Exception:
                file_size_mb = None
    
    # Update approval status
    banner.is_approved = True
    
    try:
        db.commit()
        db.refresh(banner)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    # Smart notification based on banner type - approval is celebration worthy
    if has_link:
        # Promotional banner approved - HIGH ENGAGEMENT
        push_notification(
            db,
            message=f"🎉 PROMOTIONAL banner '{banner_name}' APPROVED & LIVE! Ready for clicks! 🚀",
            type_="promotional_banner_approved",
            entity_id=banner.id,
            extra_data={
                "banner_name": banner_name,
                "has_link": True,
                "banner_link": banner_link,
                "was_pending": True,
                "now_live": True,
                "file_size_mb": file_size_mb,
                "admin_action": True,
                "approved_by": getattr(user, 'id', 'admin'),
                "banner_type": "promotional",
                "action": "promotional_banner_approved",
                "impact_level": "high",
                "status_change": "pending_to_live",
                "engagement_potential": "high",
                "revenue_potential": "high" if has_link else "none"
            }
        )
    else:
        # Standard banner approved - MEDIUM ENGAGEMENT
        push_notification(
            db,
            message=f"✅ Banner '{banner_name}' APPROVED & LIVE! 🎊",
            type_="banner_approved",
            entity_id=banner.id,
            extra_data={
                "banner_name": banner_name,
                "has_link": False,
                "was_pending": True,
                "now_live": True,
                "file_size_mb": file_size_mb,
                "admin_action": True,
                "approved_by": getattr(user, 'id', 'admin'),
                "banner_type": "standard",
                "action": "banner_approved",
                "impact_level": "medium",
                "status_change": "pending_to_live",
                "engagement_potential": "medium",
                "revenue_potential": "none"
            }
        )
    
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
    
    # Store banner data for notification context
    banner_name = banner.name
    has_link = bool(banner.banner_link)
    banner_link = banner.banner_link
    
    # Calculate file size if possible
    file_size_mb = None
    if banner.banner_image:
        file_path = banner.banner_image.lstrip('/')
        if os.path.exists(file_path):
            try:
                file_size_mb = round(os.path.getsize(file_path) / (1024 * 1024), 2)
            except Exception:
                file_size_mb = None
    
    # Update approval status
    banner.is_approved = False
    db.commit()
    db.refresh(banner)
    
    # Smart notification based on banner type - unapproval is always significant
    if has_link:
        # Promotional banner unapproved - HIGH IMPACT
        push_notification(
            db,
            message=f"🚫 PROMOTIONAL banner '{banner_name}' UNAPPROVED by admin - taken offline!",
            type_="promotional_banner_unapproved",
            entity_id=banner.id,
            extra_data={
                "banner_name": banner_name,
                "has_link": True,
                "banner_link": banner_link,
                "was_live": True,
                "now_pending": True,
                "file_size_mb": file_size_mb,
                "admin_action": True,
                "unapproved_by": getattr(user, 'id', 'admin'),
                "banner_type": "promotional",
                "action": "promotional_banner_unapproved",
                "impact_level": "high",
                "status_change": "live_to_pending"
            }
        )
    else:
        # Standard banner unapproved - MEDIUM IMPACT
        push_notification(
            db,
            message=f"🚫 Banner '{banner_name}' UNAPPROVED by admin - taken offline",
            type_="banner_unapproved",
            entity_id=banner.id,
            extra_data={
                "banner_name": banner_name,
                "has_link": False,
                "was_live": True,
                "now_pending": True,
                "file_size_mb": file_size_mb,
                "admin_action": True,
                "unapproved_by": getattr(user, 'id', 'admin'),
                "banner_type": "standard",
                "action": "banner_unapproved",
                "impact_level": "medium",
                "status_change": "live_to_pending"
            }
        )
    
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













@router.post("/spots/create")
async def create_spot_endpoint(
    location_name: str = Form(...),
    city: str = Form(...),
    state: str = Form(...),
    spot_type: str = Form(...),  # hotel, club, bar, beach
    additional_info: str = Form(""),
    cover_image: UploadFile = File(None),  # File upload
    db: Session = Depends(get_db),
    user: User = Depends(get_active_user)
):
    # Validate spot_type
    valid_types = ["hotel", "club", "foodspot", "beach"]
    if spot_type not in valid_types:
        raise HTTPException(400, f"Invalid spot type. Must be one of: {', '.join(valid_types)}")
    
    cover_image_path = None
    file_size_mb = None
    has_image = False
    
    if cover_image:
        # Validate file type
        if not cover_image.content_type.startswith('image/'):
            raise HTTPException(400, "File must be an image")
        
        # Validate file size
        content = await cover_image.read()
        if len(content) > 10 * 1024 * 1024:  # 10MB limit
            raise HTTPException(400, "Image file too large. Maximum 10MB allowed.")
        
        file_size_mb = round(len(content) / (1024 * 1024), 2)
        has_image = True
        
        # Generate unique filename
        file_extension = cover_image.filename.split('.')[-1].lower()
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        file_path = f"uploads/spots/{unique_filename}"
        
        # Save file
        os.makedirs("uploads/spots", exist_ok=True)
        try:
            with open(file_path, "wb") as buffer:
                buffer.write(content)
            
            cover_image_path = file_path
        except Exception as e:
            raise HTTPException(500, f"Failed to save image: {str(e)}")

    new_spot = Spot(
        location_name=location_name,
        city=city,
        state=state,
        spot_type=spot_type,
        additional_info=additional_info,
        cover_image=cover_image_path,
    )

    try:
        db.add(new_spot)
        db.commit()
        db.refresh(new_spot)
    except Exception as e:
        # Clean up uploaded file if database operation fails
        if cover_image_path and os.path.exists(cover_image_path):
            os.remove(cover_image_path)
        raise HTTPException(500, f"Database error: {str(e)}")

    # Smart notification based on spot type and characteristics
    location_full = f"{location_name}, {city}, {state}"
    
    # Define spot type emojis and priorities
    spot_emojis = {
        "hotel": "🏨",
        "club": "🎭", 
        "foodspot": "🍽️",
        "beach": "🏖️"
    }
    
    spot_emoji = spot_emojis.get(spot_type, "📍")
    
    if spot_type == "club":
        # Nightlife/entertainment - high engagement potential
        push_notification(
            db,
            message=f"🎭 New CLUB spot '{location_name}' added in {city}, {state}!",
            type_="club_spot_created",
            entity_id=new_spot.id,
            extra_data={
                "location_name": location_name,
                "city": city,
                "state": state,
                "spot_type": "club",
                "location_full": location_full,
                "has_image": has_image,
                "file_size_mb": file_size_mb,
                "has_additional_info": bool(additional_info.strip()),
                "created_by": getattr(user, 'id', 'user'),
                "category": "nightlife",
                "engagement_potential": "high",
                "action": "club_spot_created"
            }
        )
    elif spot_type == "beach":
        # Tourist/recreation - high interest
        push_notification(
            db,
            message=f"🏖️ New BEACH spot '{location_name}' added in {city}, {state}!",
            type_="beach_spot_created",
            entity_id=new_spot.id,
            extra_data={
                "location_name": location_name,
                "city": city,
                "state": state,
                "spot_type": "beach",
                "location_full": location_full,
                "has_image": has_image,
                "file_size_mb": file_size_mb,
                "has_additional_info": bool(additional_info.strip()),
                "created_by": getattr(user, 'id', 'user'),
                "category": "recreation",
                "engagement_potential": "high",
                "action": "beach_spot_created"
            }
        )
    elif spot_type == "hotel":
        # Accommodation - business/travel focus
        push_notification(
            db,
            message=f"🏨 New HOTEL spot '{location_name}' added in {city}, {state}",
            type_="hotel_spot_created",
            entity_id=new_spot.id,
            extra_data={
                "location_name": location_name,
                "city": city,
                "state": state,
                "spot_type": "hotel",
                "location_full": location_full,
                "has_image": has_image,
                "file_size_mb": file_size_mb,
                "has_additional_info": bool(additional_info.strip()),
                "created_by": getattr(user, 'id', 'user'),
                "category": "accommodation",
                "engagement_potential": "medium",
                "action": "hotel_spot_created"
            }
        )
    elif spot_type == "foodspot":
        # Dining - social/lifestyle focus
        push_notification(
            db,
            message=f"🍽️ New FOOD spot '{location_name}' added in {city}, {state}!",
            type_="foodspot_created",
            entity_id=new_spot.id,
            extra_data={
                "location_name": location_name,
                "city": city,
                "state": state,
                "spot_type": "foodspot",
                "location_full": location_full,
                "has_image": has_image,
                "file_size_mb": file_size_mb,
                "has_additional_info": bool(additional_info.strip()),
                "created_by": getattr(user, 'id', 'user'),
                "category": "dining",
                "engagement_potential": "high",
                "action": "foodspot_created"
            }
        )

    return {
        "message": "Spot created successfully", 
        "spot_id": new_spot.id,
        "spot_type": spot_type,
        "location": location_full,
        "has_image": has_image
    }







@router.get("/spots")
async def get_all_spots(
    spot_id: Optional[int] = Query(None, description="Filter by specific spot ID"),
    db: Session = Depends(get_db)
):
    """
    Get all spots or filter by specific spot ID
    
    Args:
        spot_id: Optional spot ID to filter by specific spot
        db: Database session
    
    Returns:
        List of spots or single spot if ID provided
    """
    
    # If spot_id is provided, return specific spot
    if spot_id is not None:
        spot = db.query(Spot).filter(Spot.id == spot_id).first()
        if not spot:
            raise HTTPException(status_code=404, detail=f"Spot with ID {spot_id} not found")
        return [spot]  # Return as list for consistent response format
    
    # Otherwise return all spots
    spots = db.query(Spot).all()
    return spots



@router.get("/spots/type/{spot_type}")
async def get_spots_by_type(
    spot_type: str,
    db: Session = Depends(get_db)
):
    # Validate spot_type
    valid_types = ["hotel", "club", "foodspot", "beach"]
    if spot_type not in valid_types:
        raise HTTPException(400, f"Invalid spot type. Must be one of: {', '.join(valid_types)}")
    
    spots = db.query(Spot).filter(Spot.spot_type == spot_type).all()
    return spots





from typing import Optional
import os
import uuid
from fastapi import Form, File, UploadFile, HTTPException, Depends
from sqlalchemy.orm import Session


@router.put("/spots/edit/{spot_id}")
async def edit_spot_endpoint(
    spot_id: int,
    location_name: str = Form(...),
    city: str = Form(...),
    state: str = Form(...),
    spot_type: str = Form(...),  # hotel, club, bar, beach
    additional_info: str = Form(""),
    cover_image: UploadFile = File(None),  # Optional file upload
    db: Session = Depends(get_db),
    user: User = Depends(get_active_user)
):
    # Check if spot exists
    existing_spot = db.query(Spot).filter(Spot.id == spot_id).first()
    if not existing_spot:
        raise HTTPException(404, "Spot not found")
    
    # Check if user owns the spot (optional authorization check)
    if existing_spot.user_id != user.id:
        raise HTTPException(403, "You can only edit your own spots")
    
    # Validate spot_type
    valid_types = ["hotel", "club", "foodspot", "beach"]
    if spot_type not in valid_types:
        raise HTTPException(400, f"Invalid spot type. Must be one of: {', '.join(valid_types)}")
    
    # Store original values for change tracking
    changes_made = []
    original_spot_type = existing_spot.spot_type
    
    if existing_spot.location_name != location_name:
        changes_made.append("location name")
    if existing_spot.city != city:
        changes_made.append("city")
    if existing_spot.state != state:
        changes_made.append("state")
    if existing_spot.spot_type != spot_type:
        changes_made.append("spot type")
    if existing_spot.additional_info != additional_info:
        changes_made.append("additional info")
    
    # Handle image update if provided
    image_updated = False
    file_size_mb = None
    
    if cover_image:
        # Validate file type
        if not cover_image.content_type.startswith('image/'):
            raise HTTPException(400, "File must be an image")
        
        # Validate file size
        content = await cover_image.read()
        if len(content) > 10 * 1024 * 1024:  # 10MB limit
            raise HTTPException(400, "Image file too large. Maximum 10MB allowed.")
        
        file_size_mb = round(len(content) / (1024 * 1024), 2)
        
        # Delete old image if it exists
        if existing_spot.cover_image:
            old_file_path = f"uploads/spots/{existing_spot.cover_image.split('/')[-1]}"
            if os.path.exists(old_file_path):
                os.remove(old_file_path)
        
        # Generate unique filename for new image
        file_extension = cover_image.filename.split('.')[-1].lower()
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        file_path = f"uploads/spots/{unique_filename}"
        
        # Save new file
        os.makedirs("uploads/spots", exist_ok=True)
        try:
            with open(file_path, "wb") as buffer:
                buffer.write(content)
            
            existing_spot.cover_image = file_path
            changes_made.append("cover image")
            image_updated = True
        except Exception as e:
            raise HTTPException(500, f"Failed to save image: {str(e)}")
    
    # Update other fields
    existing_spot.location_name = location_name
    existing_spot.city = city
    existing_spot.state = state
    existing_spot.spot_type = spot_type
    existing_spot.additional_info = additional_info

    try:
        db.commit()
        db.refresh(existing_spot)
    except Exception as e:
        # Clean up uploaded file if database operation fails
        if image_updated and existing_spot.cover_image and os.path.exists(existing_spot.cover_image):
            os.remove(existing_spot.cover_image)
        raise HTTPException(500, f"Database error: {str(e)}")

    # Smart push notification based on spot type and changes
    location_full = f"{location_name}, {city}, {state}"
    
    # Define spot type emojis
    spot_emojis = {
        "hotel": "🏨",
        "club": "🎭", 
        "foodspot": "🍽️",
        "beach": "🏖️"
    }
    
    spot_emoji = spot_emojis.get(spot_type, "📍")
    
    # Create push notifications based on what was updated
    if changes_made:
        changes_text = ", ".join(changes_made)
        
        if spot_type == "club":
            # High engagement for club updates
            push_notification(
                db,
                message=f"🎭 CLUB '{location_name}' in {city} has been UPDATED! Changes: {changes_text}",
                type_="club_spot_updated",
                entity_id=existing_spot.id,
                extra_data={
                    "location_name": location_name,
                    "city": city,
                    "state": state,
                    "spot_type": "club",
                    "location_full": location_full,
                    "changes_made": changes_made,
                    "image_updated": image_updated,
                    "file_size_mb": file_size_mb,
                    "has_additional_info": bool(additional_info.strip()),
                    "updated_by": getattr(user, 'id', 'user'),
                    "category": "nightlife",
                    "engagement_potential": "high",
                    "action": "club_spot_updated",
                    "original_spot_type": original_spot_type
                }
            )
        elif spot_type == "beach":
            push_notification(
                db,
                message=f"🏖️ BEACH '{location_name}' in {city} has been UPDATED! Changes: {changes_text}",
                type_="beach_spot_updated",
                entity_id=existing_spot.id,
                extra_data={
                    "location_name": location_name,
                    "city": city,
                    "state": state,
                    "spot_type": "beach",
                    "location_full": location_full,
                    "changes_made": changes_made,
                    "image_updated": image_updated,
                    "file_size_mb": file_size_mb,
                    "has_additional_info": bool(additional_info.strip()),
                    "updated_by": getattr(user, 'id', 'user'),
                    "category": "recreation",
                    "engagement_potential": "high",
                    "action": "beach_spot_updated",
                    "original_spot_type": original_spot_type
                }
            )
        elif spot_type == "hotel":
            push_notification(
                db,
                message=f"🏨 HOTEL '{location_name}' in {city} updated. Changes: {changes_text}",
                type_="hotel_spot_updated",
                entity_id=existing_spot.id,
                extra_data={
                    "location_name": location_name,
                    "city": city,
                    "state": state,
                    "spot_type": "hotel",
                    "location_full": location_full,
                    "changes_made": changes_made,
                    "image_updated": image_updated,
                    "file_size_mb": file_size_mb,
                    "has_additional_info": bool(additional_info.strip()),
                    "updated_by": getattr(user, 'id', 'user'),
                    "category": "accommodation",
                    "engagement_potential": "medium",
                    "action": "hotel_spot_updated",
                    "original_spot_type": original_spot_type
                }
            )
        elif spot_type == "foodspot":
            push_notification(
                db,
                message=f"🍽️ FOOD SPOT '{location_name}' in {city} has been UPDATED! Changes: {changes_text}",
                type_="foodspot_updated",
                entity_id=existing_spot.id,
                extra_data={
                    "location_name": location_name,
                    "city": city,
                    "state": state,
                    "spot_type": "foodspot",
                    "location_full": location_full,
                    "changes_made": changes_made,
                    "image_updated": image_updated,
                    "file_size_mb": file_size_mb,
                    "has_additional_info": bool(additional_info.strip()),
                    "updated_by": getattr(user, 'id', 'user'),
                    "category": "dining",
                    "engagement_potential": "high",
                    "action": "foodspot_updated",
                    "original_spot_type": original_spot_type
                }
            )

    return {
        "message": "Spot updated successfully", 
        "spot_id": existing_spot.id,
        "spot_type": spot_type,
        "location": location_full,
        "changes_made": changes_made,
        "image_updated": image_updated
    }
