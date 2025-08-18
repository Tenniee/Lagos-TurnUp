from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.email import EmailLog, OTPRecord


def create_email_log(db: Session, to_email: str, from_email: str, subject: str, 
                    email_type: str, recipient_name: str = None, sender_name: str = None):
    """Create a new email log entry"""
    new_email_log = EmailLog(
        to_email=to_email,
        from_email=from_email,
        subject=subject,
        email_type=email_type,
        recipient_name=recipient_name,
        sender_name=sender_name
    )
    db.add(new_email_log)
    db.commit()
    db.refresh(new_email_log)
    return new_email_log


def update_email_status(db: Session, email_id: int, status: str, 
                       resend_id: str = None, error_message: str = None):
    """Update email status"""
    email_log = db.query(EmailLog).filter(EmailLog.id == email_id).first()
    if email_log:
        email_log.status = status
        if resend_id:
            email_log.resend_id = resend_id
        if error_message:
            email_log.error_message = error_message
        if status == "sent":
            email_log.sent_at = datetime.utcnow()
        if status == "failed":
            email_log.retry_count += 1
        
        db.commit()
        db.refresh(email_log)
    return email_log


def get_email_log(db: Session, email_id: int):
    """Get email log by ID"""
    return db.query(EmailLog).filter(EmailLog.id == email_id).first()


def get_email_logs_by_recipient(db: Session, to_email: str, limit: int = 50):
    """Get email logs for a recipient"""
    return (db.query(EmailLog)
            .filter(EmailLog.to_email == to_email)
            .order_by(EmailLog.created_at.desc())
            .limit(limit)
            .all())


def create_otp_record(db: Session, email: str, otp_code: str, expires_at: datetime):
    """Create a new OTP record"""
    # Mark existing OTPs as expired
    db.query(OTPRecord).filter(
        and_(OTPRecord.email == email, 
             OTPRecord.is_used == False, 
             OTPRecord.is_expired == False)
    ).update({"is_expired": True})
    
    new_otp = OTPRecord(
        email=email,
        otp_code=otp_code,
        expires_at=expires_at
    )
    db.add(new_otp)
    db.commit()
    db.refresh(new_otp)
    return new_otp


def get_valid_otp(db: Session, email: str, otp_code: str):
    """Get valid OTP record"""
    return (db.query(OTPRecord)
            .filter(
                and_(
                    OTPRecord.email == email,
                    OTPRecord.otp_code == otp_code,
                    OTPRecord.is_used == False,
                    OTPRecord.is_expired == False,
                    OTPRecord.expires_at > datetime.utcnow()
                )
            )
            .first())


def mark_otp_as_used(db: Session, otp_record: OTPRecord):
    """Mark OTP as used"""
    otp_record.is_used = True
    otp_record.used_at = datetime.utcnow()
    db.commit()
    db.refresh(otp_record)
    return otp_record


def cleanup_expired_otps(db: Session):
    """Clean up expired OTPs"""
    count = (db.query(OTPRecord)
             .filter(OTPRecord.expires_at < datetime.utcnow())
             .update({"is_expired": True}))
    db.commit()
    return count