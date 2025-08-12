from pydantic import BaseModel, EmailStr


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
    access_token: str
    token_type: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

from pydantic import BaseModel

class Token(BaseModel):
    access_token: str
    token_type: str
