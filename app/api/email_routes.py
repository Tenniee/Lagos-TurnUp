# app/routers/__init__.py
# Empty file to make this a package

# app/routers/email_routes.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import logging

from app.deps.deps import get_db
from app.schemas.email import (
    CustomEmailRequest, OTPEmailRequest, OTPVerificationRequest,
    EmailResponse, OTPResponse, OTPVerificationResponse
)
from app.service import email_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/email", tags=["Email"])


@router.post("/send-custom-email", response_model=EmailResponse)
async def send_custom_email_endpoint(
    email_request: CustomEmailRequest,
    db: Session = Depends(get_db)
):
    """Send custom message email"""
    try:
        logger.info(f"=== Route handler called ===")
        logger.info(f"Request received: {email_request}")
        logger.info(f"Request type: {type(email_request)}")
        
        # Log individual fields
        logger.info(f"to_email: {getattr(email_request, 'to_email', 'MISSING')}")
        logger.info(f"subject: {getattr(email_request, 'subject', 'MISSING')}")
        logger.info(f"recipient_name: {getattr(email_request, 'recipient_name', 'MISSING')}")
        logger.info(f"sender_name: {getattr(email_request, 'sender_name', 'MISSING')}")
        logger.info(f"custom_message: {getattr(email_request, 'custom_message', 'MISSING')}")
        
        logger.info(f"About to call send_custom_email function...")

        # Send email directly (not in background) for better error handling
        result = await email_service.send_custom_email(db, email_request)
        logger.info(f"send_custom_email completed successfully: {result}")
        return EmailResponse(**result)
    except Exception as e:
        logger.error(f"❌ Route handler error: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error args: {e.args}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send-otp-email", response_model=OTPResponse)
async def send_otp_email(
    email_request: OTPEmailRequest,
    db: Session = Depends(get_db)
):
    """Send OTP email for password reset"""
    try:
        # Send email directly (not in background) for better error handling
        result = await email_service.send_otp_email(db, email_request)
        return OTPResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/verify-otp", response_model=OTPVerificationResponse)
def verify_otp(
    verification_request: OTPVerificationRequest,
    db: Session = Depends(get_db)
):
    """Verify OTP for password reset"""
    try:
        result = email_service.verify_otp(
            db=db,
            email=verification_request.email,
            otp_code=verification_request.otp
        )
        return OTPVerificationResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "email-service"}