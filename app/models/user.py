from sqlalchemy import Column, Integer, String, Boolean
from app.core.database import Base

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
    