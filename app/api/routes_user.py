from fastapi import APIRouter, Depends, status

from sqlalchemy.orm import Session
from app.schemas.user import UserCreate, UserOut, UserLogin, Token
from app.crud.user import create_user, get_users
from app.deps.deps import get_db
from typing import List
from app.utils.jwt_handler import create_access_token, decode_access_token
from app.crud.user import get_current_user, verify_password
from app.models.user import User
from fastapi import HTTPException
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer




router = APIRouter()



pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

def Log_user_in(db: Session, user_credentials: UserLogin):
    user = db.query(User).filter(User.email == user_credentials.email).first()
    if not user:
        return None  # User not found
    if not verify_password(user_credentials.password, user.password):
        return None  # Password incorrect
    return user 
@router.post("/token")
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    # Use the email as username (OAuth2PasswordRequestForm uses 'username' field)
    user_credentials = UserLogin(email=form_data.username, password=form_data.password)
    user = Log_user_in(db, user_credentials)
    
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(user_id=user.id)
    return {"access_token": access_token, "token_type": "bearer"}





@router.post("/sub-admin-signup", response_model=UserOut)
def create_new_user(user: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = create_user(db, user)

    # create a token with user.id embedded
    access_token = create_access_token(user_id= new_user.id)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "id": new_user.id,
        "first_name": new_user.first_name,
        "last_name": new_user.last_name,
        "email": new_user.email,
        "role": new_user.role
    }




@router.get("/get-sub-admin", response_model=List[UserOut])
def list_users(db: Session = Depends(get_db)):
    return get_users(db)



def authenticate_user(db: Session, email: str, password: str):
    # Find user by email
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None
    # Verify hashed password
    if not pwd_context.verify(password, user.password):
        return None
    return user

@router.post("/sub-admin-login", response_model=Token)
def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    # Authenticate
    user = authenticate_user(db, user_credentials.email, user_credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Create access token
    access_token = create_access_token(user_id= user.id)
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserOut)
def fetch_current_user_details(current_user: UserOut = Depends(get_current_user)):
    return current_user