# routes/google_auth.py
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.utils.google_auth import GoogleOAuthService
from app.crud.google_integration import GoogleIntegrationService

# Import your existing dependencies
from app.deps.deps import get_db  # Your existing database dependency
from app.utils.jwt_handler import create_access_token  # Your existing JWT function
from app.crud.user import get_current_user  # Your existing auth dependency
from app.models.user import User

router = APIRouter(prefix="/auth/google", tags=["Google Auth"])

@router.get("/login")
async def google_login():
    """
    Get Google OAuth login URL
    Frontend should redirect user to this URL
    """
    try:
        google_service = GoogleOAuthService()
        auth_url = google_service.get_google_auth_url()
        return {
            "auth_url": auth_url,
            "message": "Redirect user to this URL to start Google OAuth"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate Google auth URL: {str(e)}"
        )


@router.get("/callback")
async def google_callback(
    code: str = Query(..., description="Authorization code from Google"),
    state: str = Query(None, description="Optional state parameter"),
    db: Session = Depends(get_db)
):
    """
    Handle Google OAuth callback
    This is where Google redirects after user authorizes
    """
    try:
        # Initialize services
        google_service = GoogleOAuthService()
        integration_service = GoogleIntegrationService(db)
        
        # Exchange code for tokens
        tokens = await google_service.exchange_code_for_tokens(code)
        
        # Get user info from Google
        user_info = await google_service.get_user_info(tokens["access_token"])
        
        # Find or create user
        user, is_new = integration_service.find_or_create_user_from_google(
            user_info, tokens
        )
        
        # Create JWT token using your existing system
        access_token = create_access_token(user_id={"sub": str(user.id)})
        
        # Get frontend URL from environment or use default
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        
        # Redirect to frontend with token and user info
        if is_new:
            # New user - redirect to onboarding or welcome page
            redirect_url = f"{frontend_url}/welcome?token={access_token}&new_user=true"
        else:
            # Existing user - redirect to dashboard
            redirect_url = f"{frontend_url}/dashboard?token={access_token}"
        
        return RedirectResponse(url=redirect_url, status_code=302)
        
    except ValueError as e:
        # Handle business logic errors - redirect to frontend with error
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        error_url = f"{frontend_url}/login?error=auth_failed&message={str(e)}"
        return RedirectResponse(url=error_url, status_code=302)
        
    except Exception as e:
        # Handle unexpected errors - redirect to frontend with error
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        error_url = f"{frontend_url}/login?error=server_error&message=Authentication failed"
        return RedirectResponse(url=error_url, status_code=302)
        


@router.post("/link" )
async def link_google_account(
    current_user: User = Depends(get_current_user),  # Uncomment and use your auth dependency
    db: Session = Depends(get_db)
):
    """
    Generate URL to link Google account to existing logged-in user
    User must be already authenticated to use this endpoint
    """
    try:
        google_service = GoogleOAuthService()
        
        # You can include user info in state for linking after callback
        state = f"link_user_{current_user.id}"
        state = "link_account"  # Simplified for now
        
        auth_url = google_service.get_google_auth_url(state=state)
        return {
            "auth_url": auth_url,
            "message": "Redirect user to this URL to link their Google account"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate linking URL: {str(e)}"
        )

@router.delete("/unlink")
async def unlink_google_account(
    current_user: User = Depends(get_current_user),  # Uncomment and use your auth dependency
    db: Session = Depends(get_db)
):
    """
    Remove Google account linking for current user
    User must be already authenticated to use this endpoint
    """
    try:
        integration_service = GoogleIntegrationService(db)
        
        # For now, using a placeholder user_id - replace with current_user.id
        success = integration_service.unlink_google_account(current_user.id)
        
        return {
            "message": "Google account unlinked successfully" # if success else "No Google account linked"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unlink Google account: {str(e)}"
        )

@router.get("/status", response_model=None)
async def google_auth_status(
    current_user:User = Depends(get_current_user),  # Uncomment and use your auth dependency
    db: Session = Depends(get_db)
):
    """
    Check if current user has Google account linked
    """
    try:
        integration_service = GoogleIntegrationService(db)
        
        # For now, using a placeholder - replace with current_user.id
        google_auth = integration_service.get_google_auth_by_user_id(current_user.id)
        
        return {
            "has_google_linked": google_auth is not None,
            "google_email": google_auth.email if google_auth else None,
            "google_name": google_auth.name if google_auth else None,
            "message": "Replace with actual user authentication"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check Google auth status: {str(e)}"
        )