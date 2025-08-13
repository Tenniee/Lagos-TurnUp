from sqlalchemy.orm import Session
from app.models.user import User
from fastapi.security import OAuth2PasswordBearer
from app.schemas.user import UserCreate, UserLogin
from passlib.context import CryptContext
from fastapi import APIRouter, Depends
from app.deps.deps import get_db
from app.utils.jwt_handler import create_access_token, decode_access_token
from fastapi import HTTPException

# Setup for password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def create_user(db: Session, user_data: dict, profile_picture_path: str = None):
    hashed_password = hash_password(user_data["password"])
    new_user = User(
        first_name=user_data["first_name"],
        last_name=user_data["last_name"],
        email=user_data["email"], 
        password=hashed_password,
        role=user_data["role"],
        profile_picture=profile_picture_path
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user
    

def get_users(db: Session, skip: int = 0, limit: int = 10):
    return db.query(User).offset(skip).limit(limit).all()







def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def Log_user_in(db: Session, user_credentials: UserLogin):
    user = db.query(User).filter(User.email == user_credentials.email).first()
    if not user:
        return None  # User not found
    if not verify_password(user_credentials.password, user.password):
        return None  # Password incorrect
    return user  # Login successful




def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        user_id = decode_access_token(token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user