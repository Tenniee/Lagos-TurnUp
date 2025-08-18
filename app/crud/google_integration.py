# auth/google_integration.py
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.user import User, GoogleAuth  
from app.crud.user import hash_password  
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
import secrets
import string

class GoogleIntegrationService:
    def __init__(self, db: Session):
        self.db = db
    
    def find_or_create_user_from_google(
        self, 
        google_data: Dict[str, Any], 
        tokens: Dict[str, Any]
    ) -> Tuple[User, bool]:
        """
        Find existing user or create new one from Google data
        Returns: (user, is_new_user)
        """
        google_id = google_data["id"]
        email = google_data["email"]
        
        # Check if this Google account already exists
        existing_google_auth = self.db.query(GoogleAuth).filter(
            GoogleAuth.id == google_id
        ).first()
        
        if existing_google_auth and existing_google_auth.user_id:
            # Get the linked user
            user = self.db.query(User).filter(
                User.id == existing_google_auth.user_id
            ).first()
            
            if user:
                # Update tokens
                self._update_google_tokens(existing_google_auth, tokens, google_data)
                self.db.commit()
                return user, False
        
        # Check if user with this email exists in your system
        existing_user = self.db.query(User).filter(User.email == email).first()
        
        if existing_user:
            # Link Google account to existing user
            if existing_google_auth:
                existing_google_auth.user_id = existing_user.id
                self._update_google_tokens(existing_google_auth, tokens, google_data)
            else:
                self._create_google_auth_record(google_id, existing_user.id, google_data, tokens)
            
            self.db.commit()
            return existing_user, False
        
        # Create new user
        new_user = self._create_user_from_google(google_data)
        self.db.add(new_user)
        self.db.flush()  # Get the user ID
        
        # Create Google auth record
        if existing_google_auth:
            existing_google_auth.user_id = new_user.id
            self._update_google_tokens(existing_google_auth, tokens, google_data)
        else:
            self._create_google_auth_record(google_id, new_user.id, google_data, tokens)
        
        self.db.commit()
        return new_user, True
    
    def _create_user_from_google(self, google_data: Dict[str, Any]) -> User:
        """
        Create a new user from Google data
        Adapted to match your User model with first_name/last_name
        """
        # Parse the full name from Google into first_name and last_name
        full_name = google_data.get("name", "")
        name_parts = full_name.split(" ", 1) if full_name else ["", ""]
        first_name = name_parts[0] if len(name_parts) > 0 else ""
        last_name = name_parts[1] if len(name_parts) > 1 else ""
        
        # Generate a random password for Google OAuth users
        # This ensures they have a password for your update-password endpoint
        random_password = ''.join(secrets.choice(string.ascii_letters + string.digits + "!@#$%^&*") for _ in range(16))
        hashed_password = hash_password(random_password)  # Now this will work
        
        return User(
            first_name=first_name,
            last_name=last_name,
            email=google_data["email"],
            password=hashed_password,  # Random secure password
            role="user",  # Default role (you might want to adjust this)
            is_deactivated=False,
            profile_picture=google_data.get("picture"),  # Google profile picture URL
        )

    def _create_google_auth_record(
        self, 
        google_id: str, 
        user_id: str, 
        google_data: Dict[str, Any], 
        tokens: Dict[str, Any]
    ) -> GoogleAuth:
        """Create new Google auth record"""
        
        # Check for email conflicts (since we can't use UNIQUE constraint)
        existing_email = self.db.query(GoogleAuth).filter(
            and_(GoogleAuth.email == google_data["email"], GoogleAuth.id != google_id)
        ).first()
        
        if existing_email:
            raise ValueError(f"Email {google_data['email']} already linked to another Google account")
        
        expires_at = None
        if tokens.get("expires_in"):
            expires_at = datetime.utcnow() + timedelta(seconds=int(tokens["expires_in"]))
        
        # Parse name for the GoogleAuth record too
        full_name = google_data.get("name", "")
        
        google_auth = GoogleAuth(
            id=google_id,
            user_id=user_id,
            email=google_data["email"],
            name=full_name,  # Keep full name in GoogleAuth record
            picture=google_data.get("picture"),
            access_token=tokens.get("access_token"),
            refresh_token=tokens.get("refresh_token"),
            token_expires_at=expires_at,
        )
        
        self.db.add(google_auth)
        return google_auth
    
    def _update_google_tokens(
        self, 
        google_auth: GoogleAuth, 
        tokens: Dict[str, Any], 
        google_data: Dict[str, Any]
    ):
        """Update existing Google auth record"""
        google_auth.access_token = tokens.get("access_token")
        if tokens.get("refresh_token"):
            google_auth.refresh_token = tokens.get("refresh_token")
        
        if tokens.get("expires_in"):
            google_auth.token_expires_at = datetime.utcnow() + timedelta(
                seconds=int(tokens["expires_in"])
            )
        
        # Update profile info
        google_auth.name = google_data.get("name", google_auth.name)
        google_auth.picture = google_data.get("picture", google_auth.picture)
    
    def get_google_auth_by_user_id(self, user_id: str) -> Optional[GoogleAuth]:
        """Get Google auth record for a user"""
        return self.db.query(GoogleAuth).filter(GoogleAuth.user_id == user_id).first()
    
    def unlink_google_account(self, user_id: str) -> bool:
        """Remove Google auth for a user"""
        google_auth = self.get_google_auth_by_user_id(user_id)
        if google_auth:
            self.db.delete(google_auth)
            self.db.commit()
            return True
        return False