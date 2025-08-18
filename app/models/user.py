from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime
from app.core.database import Base
from datetime import datetime


class User(Base):
    __tablename__ = "sub_admins"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    email = Column(String(100), unique=True, nullable=False)
    password = Column(String(200), nullable=False)
    role = Column(String(50), default="sub-admin", nullable=False)
    is_deactivated = Column(Boolean, default=False, nullable=False)
    profile_picture = Column(String(500), nullable=True)  # Add this line
    




class GoogleAuth(Base):
    __tablename__ = "google_auth"
    
    id = Column(String(255), primary_key=True)  # Google's user ID
    user_id = Column(String(255))  # Link to your User.id
    email = Column(String(320), nullable=False)
    name = Column(String(255))
    picture = Column(Text)
    access_token = Column(Text)
    refresh_token = Column(Text)
    token_expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
