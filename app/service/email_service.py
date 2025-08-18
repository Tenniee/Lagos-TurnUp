# app/services/__init__.py
# Empty file to make this a package

# app/services/email_service.py
import secrets
import string
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

import resend
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.utils.template_utils import render_template
from app.crud import email

logger = logging.getLogger(__name__)

# Configure Resend
resend.api_key = settings.RESEND_API_KEY


def generate_otp(length: int = 6) -> str:
    """Generate a random OTP"""
    return ''.join(secrets.choice(string.digits) for _ in range(settings.OTP_LENGTH))


async def send_email(to: str, subject: str, html_content: str, from_email: str = None) -> Dict[str, Any]:
    """Send email using Resend"""
    
    print("SEND_EMAIL FUNCTION CALLED!")
    
    if not from_email:
        from_email = settings.FROM_EMAIL
    
    try:
        # First test with minimal email
        print("Testing with minimal email first...")
        try:
            minimal_test = {
                "from": from_email,
                "to": [to],
                "subject": "Test",
                "text": "Simple test"
            }
            test_response = resend.Emails.send(minimal_test)
            print(f"Minimal test worked: {test_response}")
        except Exception as test_error:
            print(f"Even minimal test failed: {str(test_error)}")
            # If minimal test fails, it's definitely a config issue
            raise ValueError(f"Resend configuration issue: {str(test_error)}")
        
        # If minimal test worked, try with your actual content
        print("Minimal test passed, trying with actual content...")
        
        email_data = {
            "from": from_email,
            "to": [to],
            "subject": subject,
            "html": html_content
        }
        
        response = resend.Emails.send(email_data)
        print(f"Full email SUCCESS: {response}")
        
        return {
            "success": True,
            "resend_id": response.get("id"),
            "response": response
        }
        
    except Exception as e:
        print(f"SEND_EMAIL ERROR: {str(e)} (Type: {type(e).__name__})")
        raise Exception(f"Email service error: {str(e)}")


def prepare_custom_email_context(recipient_name: str, custom_message: str, 
                               sender_name: str) -> Dict[str, Any]:
    """Prepare context for custom email template"""
    return {
        "recipient_name": recipient_name,
        "custom_message": custom_message,
        "sender_name": sender_name,
        "current_date": datetime.now().strftime("%B %d, %Y")
    }


def prepare_otp_email_context(recipient_name: str, otp_code: str) -> Dict[str, Any]:
    """Prepare context for OTP email template"""
    return {
        "recipient_name": recipient_name,
        "otp_code": otp_code,
        "expiration_minutes": settings.OTP_EXPIRY_MINUTES
    }


async def send_custom_email(db: Session, email_request) -> Dict[str, Any]:
    """Send custom message email"""
    print("FUNCTION CALLED!")
    email_log = None
    
    try:
        logger.info(f"=== Starting email send process ===")
        logger.info(f"To: {email_request.to_email}")
        logger.info(f"Subject: {email_request.subject}")
        logger.info(f"Sender: {email_request.sender_name}")

        # Test 1: Create email log
        print("TEST 1: About to create email log")
        logger.info(f"Creating email log...")
        try:
            email_log = email.create_email_log(
                db=db,
                to_email=email_request.to_email,
                from_email=settings.FROM_EMAIL,
                subject=email_request.subject,
                email_type="custom_message",
                recipient_name=email_request.recipient_name,
                sender_name=email_request.sender_name
            )
            print(f"TEST 1 SUCCESS: Email log created with ID: {email_log.id}")
            logger.info(f"✓ Email log created with ID: {email_log.id}")
        except Exception as log_error:
            print(f"TEST 1 FAILED: {str(log_error)}")
            logger.error(f"❌ Failed to create email log: {str(log_error)}")
            raise log_error
        
        # Test 2: Prepare template context
        print("TEST 2: About to prepare template context")
        logger.info(f"Preparing template context...")
        try:
            context = prepare_custom_email_context(
                email_request.recipient_name,
                email_request.custom_message,
                email_request.sender_name
            )
            print(f"TEST 2 SUCCESS: Context prepared: {context}")
            logger.info(f"✓ Context prepared: {context}")
        except Exception as context_error:
            print(f"TEST 2 FAILED: {str(context_error)}")
            logger.error(f"❌ Failed to prepare context: {str(context_error)}")
            raise context_error
        
        # Test 3: Render template
        print("TEST 3: About to render template")
        logger.info(f"Rendering template...")
        try:
            html_content = render_template("custom_message.html", context)
            print(f"TEST 3 SUCCESS: Template rendered. Length: {len(html_content)}")
            logger.info(f"✓ Template rendered successfully. Length: {len(html_content)}")
            logger.info(f"HTML preview: {html_content[:200]}...")
        except Exception as template_error:
            print(f"TEST 3 FAILED: {str(template_error)}")
            logger.error(f"❌ Template rendering failed: {str(template_error)}")
            raise template_error

        # Test 4: Send email
        print("TEST 4: About to send email")
        logger.info(f"Calling send_email function...")
        logger.info(f"FROM_EMAIL setting: {settings.FROM_EMAIL}")
        try:
            result = await send_email(
                to=email_request.to_email,
                subject=email_request.subject,
                html_content=html_content,
                from_email=settings.FROM_EMAIL
            )
            print(f"TEST 4 SUCCESS: Email sent. Result: {result}")
            logger.info(f"✓ send_email returned: {result}")
        except Exception as send_error:
            print(f"TEST 4 FAILED: {str(send_error)}")
            logger.error(f"❌ send_email failed: {str(send_error)}")
            raise send_error
        
        # Test 5: Update email log
        print("TEST 5: About to update email status")
        logger.info(f"Updating email status to sent...")
        try:
            email.update_email_status(
                db=db,
                email_id=email_log.id,
                status="sent",
                resend_id=result.get("resend_id")
            )
            print("TEST 5 SUCCESS: Email status updated")
            logger.info(f"✓ Email status updated successfully")
        except Exception as update_error:
            print(f"TEST 5 FAILED: {str(update_error)}")
            logger.error(f"❌ Failed to update email status: {str(update_error)}")
            raise update_error
        
        print("ALL TESTS PASSED - Returning success")
        return {
            "message": "Custom email sent successfully",
            "recipient": email_request.to_email,
            "email_id": email_log.id,
            "status": "sent"
        }
        
    except Exception as e:
        print(f"EXCEPTION CAUGHT: {str(e)} (Type: {type(e).__name__})")
        logger.error(f"❌ Unexpected error in send_custom_email: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error args: {e.args}")
        
        # Update email log with error if we created one
        if email_log:
            logger.info(f"Updating email log {email_log.id} with error status...")
            email.update_email_status(
                db=db,
                email_id=email_log.id,
                status="failed",
                error_message=str(e)
            )
        
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to send email to {email_request.to_email}: {str(e)}"
        )


async def send_otp_email(db: Session, email_request) -> Dict[str, Any]:
    """Send OTP email for password reset"""
    # Generate OTP
    otp_code = generate_otp()
    expires_at = datetime.utcnow() + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)
    
    # Create OTP record
    otp_record = email.create_otp_record(
        db=db,
        email=email_request.to_email,
        otp_code=otp_code,
        expires_at=expires_at
    )
    
    # Create email log
    email_log = email.create_email_log(
        db=db,
        to_email=email_request.to_email,
        from_email=settings.FROM_EMAIL,
        subject="Password Reset OTP",
        email_type="otp_reset",
        recipient_name=email_request.recipient_name
    )
    
    try:
        # Prepare template context
        context = prepare_otp_email_context(
            email_request.recipient_name,
            otp_code
        )
        
        # Render template
        html_content = render_template("otp_reset.html", context)
        
        # Send email
        result = await send_email(
            to=email_request.to_email,
            subject="Password Reset OTP",
            html_content=html_content
        )
        
        # Update email log
        email.update_email_status(
            db=db,
            email_id=email_log.id,
            status="sent",
            resend_id=result.get("resend_id")
        )
        
        return {
            "message": "OTP email sent successfully",
            "recipient": email_request.to_email,
            "expires_in_minutes": settings.OTP_EXPIRY_MINUTES,
            "email_id": email_log.id
        }
        
    except Exception as e:
        # Update email log with error
        email.update_email_status(
            db=db,
            email_id=email_log.id,
            status="failed",
            error_message=str(e)
        )
        raise


def verify_otp(db: Session, email: str, otp_code: str) -> Dict[str, Any]:
    """Verify OTP for password reset"""
    # Get valid OTP
    otp_record = email.get_valid_otp(db, email, otp_code)
    
    if not otp_record:
        raise HTTPException(
            status_code=400, 
            detail="Invalid or expired OTP"
        )
    
    # Mark as used
    email.mark_otp_as_used(db, otp_record)
    
    return {
        "message": "OTP verified successfully",
        "email": email,
        "verified": True
    }