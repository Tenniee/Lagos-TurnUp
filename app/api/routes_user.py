from fastapi import APIRouter, Depends, status, UploadFile, Form, File

from sqlalchemy.orm import Session
from app.schemas.user import UserCreate, UserOut, UserLogin, Token, PasswordResetRequest
from fastapi import HTTPException
from app.crud.user import create_user, get_users, hash_password
from app.deps.deps import get_db
from typing import List
from app.utils.jwt_handler import create_access_token, decode_access_token
from app.crud.user import get_current_user, verify_password
from app.models.user import User
from fastapi import HTTPException
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
import uuid
import os
from typing import List, Optional
from app.utils.cloudinary import CloudinaryService


from sqlalchemy import text




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






@router.post("/admin/migrate-profile-column")
async def migrate_profile_column(db: Session = Depends(get_db)):
    """Temporary endpoint to add profile_picture_public_id column"""
    try:
        # Wrap the SQL string with text()
        db.execute(text("""
            ALTER TABLE sub_admins 
            ADD COLUMN IF NOT EXISTS profile_picture_public_id VARCHAR(255);
        """))
        db.commit()
        return {"message": "Column added successfully!"}
    except Exception as e:
        db.rollback()
        return {"error": str(e)}





async def save_profile_picture(file: UploadFile) -> dict:
    """
    Upload profile picture to Cloudinary and return URL and public_id
    """
    if not file.content_type.startswith('image/'):
        raise HTTPException(400, "File must be an image")
    
    # Read file content
    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(400, f"Error reading file: {str(e)}")
    
    # Validate file size (5MB limit for profile pictures)
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(400, "Profile picture too large. Maximum 5MB allowed.")
    
    # Upload to Cloudinary
    try:
        cloudinary_result = CloudinaryService.upload_profile_image(
            file_content=content,
            filename=file.filename or "profile"
        )
        return cloudinary_result
    except Exception as e:
        raise HTTPException(500, f"Profile picture upload failed: {str(e)}")


@router.post("/sub-admin-signup", response_model=UserOut)
async def create_new_user(
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    secret_key: str = Form(...),  # Added secret key requirement
    role: str = Form("sub-admin"),
    profile_picture: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    # Validate secret key first
    if secret_key != "TURNUP_LAGOS":
        raise HTTPException(
            status_code=401, 
            detail="Unauthorized: Invalid secret key"
        )
    
    # Check if email exists
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Handle profile picture upload
    profile_picture_url = None
    profile_picture_public_id = None
    cloudinary_result = None
    
    if profile_picture:
        try:
            cloudinary_result = await save_profile_picture(profile_picture)
            profile_picture_url = cloudinary_result["url"]
            profile_picture_public_id = cloudinary_result["public_id"]
        except HTTPException:
            raise  # Re-raise HTTP exceptions as-is
        except Exception as e:
            raise HTTPException(500, f"Profile picture processing failed: {str(e)}")

    # Create user
    hashed_password = hash_password(password)
    new_user = User(
        first_name=first_name,
        last_name=last_name,
        email=email,
        password=hashed_password,
        role=role,
        profile_picture=profile_picture_url,
        profile_picture_public_id=profile_picture_public_id  # Store for deletion later
    )
    
    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
    except Exception as e:
        # Clean up uploaded image if database operation fails
        if cloudinary_result and cloudinary_result.get("public_id"):
            try:
                CloudinaryService.delete_image(cloudinary_result["public_id"])
            except:
                pass  # Don't fail the main operation if cleanup fails
        
        db.rollback()
        raise HTTPException(500, f"Database error: {str(e)}")

    # Create token
    access_token = create_access_token(user_id=new_user.id)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "id": new_user.id,
        "first_name": new_user.first_name,
        "last_name": new_user.last_name,
        "email": new_user.email,
        "role": new_user.role,
        "profile_picture": new_user.profile_picture
    }


@router.put("/sub-admin/{user_id}", response_model=UserOut)
async def update_sub_admin(
    user_id: int,
    first_name: Optional[str] = Form(None),
    last_name: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    role: Optional[str] = Form(None),
    profile_picture: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # Assuming you have authentication
):
    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Optional: Check if current user has permission to update this user
    # You might want to restrict this based on roles or ownership
    if current_user.role not in ["admin", "super-admin"] and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to update this user")

    # Check if email is being updated and if it already exists
    if email and email != user.email:
        existing_email = db.query(User).filter(User.email == email).first()
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already registered")
        user.email = email

    # Update fields if provided
    if first_name is not None:
        user.first_name = first_name
    
    if last_name is not None:
        user.last_name = last_name
    
    if password is not None:
        user.password = hash_password(password)
    
    if role is not None:
        # Optional: Add role validation
        valid_roles = ["sub-admin", "super-admin"]
        if role not in valid_roles:
            raise HTTPException(status_code=400, detail="Invalid role")
        user.role = role

    # Handle profile picture update
    old_public_id = None
    if profile_picture:
        # Store old public_id for cleanup
        old_public_id = getattr(user, 'profile_picture_public_id', None)
        
        try:
            cloudinary_result = await save_profile_picture(profile_picture)
            user.profile_picture = cloudinary_result["url"]
            user.profile_picture_public_id = cloudinary_result["public_id"]
        except HTTPException:
            raise  # Re-raise HTTP exceptions as-is
        except Exception as e:
            raise HTTPException(500, f"Profile picture update failed: {str(e)}")

    # Update timestamp (assuming you have an updated_at field)
    # user.updated_at = datetime.utcnow()

    try:
        db.commit()
        db.refresh(user)
        
        # Clean up old profile picture after successful database update
        if old_public_id and profile_picture:
            try:
                CloudinaryService.delete_image(old_public_id)
            except:
                pass  # Don't fail the main operation if cleanup fails
                
    except Exception as e:
        # If database update fails and we uploaded a new image, clean it up
        if profile_picture and hasattr(user, 'profile_picture_public_id'):
            try:
                CloudinaryService.delete_image(user.profile_picture_public_id)
            except:
                pass
        
        db.rollback()
        raise HTTPException(500, f"Database error: {str(e)}")

    return {
        "id": user.id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "role": user.role,
        "profile_picture": user.profile_picture
    }





@router.put("/update-password")
async def update_password(
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update user password
    Requires current password verification
    """
    # Verify new passwords match
    if new_password != confirm_password:
        raise HTTPException(
            status_code=400, 
            detail="New passwords do not match"
        )
    
    # Verify current password
    if not verify_password(current_password, current_user.password):
        raise HTTPException(
            status_code=400, 
            detail="Current password is incorrect"
        )
    
    # Validate new password strength (optional)
    if len(new_password) < 8:
        raise HTTPException(
            status_code=400, 
            detail="New password must be at least 8 characters long"
        )
    
    # Update password
    current_user.password = hash_password(new_password)
    db.commit()
    
    return {
        "message": "Password updated successfully"
    }







@router.put("/reset-password-simple")
async def reset_password_simple(
    request: PasswordResetRequest,
    db: Session = Depends(get_db)
):
    """
    Simple password reset endpoint
    WARNING: This relies on frontend to only show after OTP verification
    Less secure than token-based approach
    """
    # Verify passwords match
    if request.new_password != request.confirm_password:
        raise HTTPException(
            status_code=400, 
            detail="Passwords do not match"
        )
    
    # Validate password strength
    if len(request.new_password) < 8:
        raise HTTPException(
            status_code=400, 
            detail="Password must be at least 8 characters long"
        )
    
    # Get user by email
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")  
    
    # Update password
    user.password = hash_password(request.new_password)
    db.commit()
    
    return {
        "message": "Password reset successfully",
        "email": request.email
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





# Alternative version with more detailed response
@router.delete("/delete-user/{user_id}")
def delete_user_detailed(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check if current user is super-admin
    if current_user.role != "super-admin":
        raise HTTPException(
            status_code=403, 
            detail="Access denied. Only super-admin can delete users."
        )
    
    # Find the user to delete
    user_to_delete = db.query(User).filter(User.id == user_id).first()
    if not user_to_delete:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Store user info before deletion
    deleted_user_info = {
        "id": user_to_delete.id,
        "email": user_to_delete.email,
        "first_name": user_to_delete.first_name,
        "last_name": user_to_delete.last_name,
        "role": user_to_delete.role
    }
    
    # Prevent super-admin from deleting themselves
    if user_to_delete.id == current_user.id:
        raise HTTPException(
            status_code=400, 
            detail="Cannot delete your own account"
        )
    
    # Delete the user
    db.delete(user_to_delete)
    db.commit()
    
    return {
        "message": "User deleted successfully",
        "deleted_user": deleted_user_info,
        "deleted_by": {
            "id": current_user.id,
            "email": current_user.email
        }
    }