from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError
from app.deps.deps import get_db
from app.models.user import User
from app.utils.jwt_handler import decode_access_token  # your existing function

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

def check_user_deactivated(token: str, db: Session):
    try:
        user_id = decode_access_token(token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if user.is_deactivated:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated"
        )

    return user

def get_active_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    return check_user_deactivated(token, db)