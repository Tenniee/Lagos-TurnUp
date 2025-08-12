from datetime import datetime, timedelta
from jose import JWTError, jwt

# Secret and algorithm – keep your secret key safe!
SECRET_KEY = "your_secret_key_here"  # Change this and keep it secret
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # 1 hour token lifetime

#def create_access_token(data: dict, expires_delta: timedelta = None):
#    to_encode = data.copy()
#    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
#    to_encode.update({"exp": expire})
#    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
#    return encoded_jwt


def create_access_token(user_id: int):
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"user_id": user_id, "exp": expire}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

    
def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")
        if user_id is None:
            raise ValueError("user_id not found in token")
        return user_id
    except JWTError:
        raise ValueError("Invalid or expired token")
