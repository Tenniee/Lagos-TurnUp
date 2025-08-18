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
    profile_picture: Optional[str] = None

    @computed_field
    @property
    def profile_picture_url(self) -> Optional[str]:
        if self.profile_picture:
            base_url = os.getenv("BASE_URL", "http://localhost:8000")
            return f"{base_url}{self.profile_picture}"
        return None

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