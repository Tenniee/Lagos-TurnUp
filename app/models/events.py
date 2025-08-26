from sqlalchemy import Column, Integer, String, Date, Time, Text, Boolean, DateTime, JSON, func
from sqlalchemy.sql import func
from app.core.database import Base


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=False)
    event_name = Column(String(150), nullable=False)
    state = Column(String(100), nullable=False)
    venue = Column(String(150), nullable=False)
    date = Column(Date, nullable=False)
    time = Column(String(10), nullable=False)
    dress_code = Column(String(100), nullable=True)
    event_description = Column(Text, nullable=True)
    event_flyer = Column(String(200), nullable=True)  
    is_featured = Column(Boolean, default=False)
    pending = Column(Boolean, default=True)  
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    event_flyer_public_id = Column(String(255), nullable=True)
    
    # Featured request fields
    featured_requested = Column(Boolean, default=False)  # User requested featured status
    contact_method = Column(String(20), nullable=True)  # email, phone, whatsapp
    contact_link = Column(String(300), nullable=True)



class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    message = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)
    entity_id = Column(Integer, nullable=True)  # related object ID
    extra_data = Column(JSON, nullable=True)    # optional structured data
    status = Column(String(10), default="unread")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Newsletter(Base):
    __tablename__ = "newsletters"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(100), unique=False, index=True)


class Banner(Base):
    __tablename__ = "banners"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    banner_image = Column(String(500), nullable=True)  # Store file path or URL
    banner_public_id = Column(String(255), nullable=True)
    banner_link = Column(String(500), nullable=True)  # URL link for the banner
    is_approved = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())



class Spot(Base):
    __tablename__ = "spots"

    id = Column(Integer, primary_key=True, index=False)
    location_name = Column(String(200), nullable=False)
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)
    spot_type = Column(String(20), nullable=False)  # hotel, club, bar, beach
    cover_image = Column(String(200), nullable=True)
    additional_info = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    cover_image_public_id = Column(String(255), nullable=True)
    