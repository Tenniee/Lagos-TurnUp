from pydantic import BaseModel, EmailStr, computed_field
from typing import Optional
from datetime import date, datetime
import os
from dotenv import load_dotenv
load_dotenv() 

class EventCreate(BaseModel):
    event_name: str
    state: str
    venue: str
    date: date
    time: str
    dress_code: Optional[str] = ""  # Default to empty string
    event_description: Optional[str] = ""  # Default to empty string
    is_featured: Optional[bool] = False
    event_flyer: Optional[str] = "" 


class EventOut(BaseModel):
    id: int
    event_name: str  # Changed from 'name'
    state: str
    venue: str
    date: date
    time: str
    dress_code: Optional[str] = None
    event_description: Optional[str] = None
    event_flyer: Optional[str] = None  # Changed from 'flyer_url'
    is_featured: bool = False
    # created_at: Optional[datetime] = None  # Remove this since your model doesn't have it

    @computed_field
    @property
    def flyer_url(self) -> Optional[str]:
        if self.event_flyer:
            base_url = os.getenv("BASE_URL", "http://localhost:8000")
            return f"{base_url}{self.event_flyer}"
        return None

    class Config:
        from_attributes = True  # This tells Pydantic to read from SQLAlchemy objects


class NotificationOut(BaseModel):
    id: int
    message: str
    type: str
    entity_id: Optional[int]
    extra_data: Optional[dict]
    status: str
    created_at: datetime

    class Config:
        orm_mode = True


class NewsletterCreate(BaseModel):
    email: EmailStr


class EventUpdateSchema(BaseModel):
    event_name: Optional[str] 
    state: Optional[str] 
    venue: Optional[str] 
    date: Optional[date] 
    time: Optional[str] 
    dress_code: Optional[str] = None
    event_description: Optional[str] 
    is_featured: Optional[bool] = None
    event_flyer: Optional[str] = None






class BannerCreate(BaseModel):
    name: str

class BannerUpdate(BaseModel):
    name: Optional[str] = None

class BannerOut(BaseModel):
    id: int
    name: str
    banner_image: Optional[str] = None
    is_approved: bool = False
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def banner_url(self) -> Optional[str]:
        if self.banner_image:
            base_url = os.getenv("BASE_URL", "http://localhost:8000")
            return f"{base_url}{self.banner_image}"
        return None

    class Config:
        from_attributes = True