from pydantic import BaseModel, EmailStr, computed_field
from typing import Optional
import os


class UserCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str
    role: str = "sub-admin"  



class UserOut(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
    role: str
    profile_picture: Optional[str] = None  # This already contains the full Cloudinary URL
    is_deactivated: bool = False

    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    email: EmailStr
    password: str

from pydantic import BaseModel

class Token(BaseModel):
    access_token: str
    token_type: str


class PasswordResetRequest(BaseModel):
    email: EmailStr
    new_password: str
    confirm_password: str

class PasswordResetVerify(BaseModel):
    email: EmailStr
    otp: str
    new_password: str