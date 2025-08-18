from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.sql import func

from app.core.database import Base


class EmailLog(Base):
    """Model to track sent emails"""
    __tablename__ = "email_logs"

    id = Column(Integer, primary_key=True, index=True)
    to_email = Column(String(255), nullable=False)
    from_email = Column(String(255), nullable=False)
    subject = Column(String(500), nullable=False)
    email_type = Column(String(50), nullable=False)  # custom_message, otp_reset, etc.
    status = Column(String(20), default="pending")  # pending, sent, failed
    resend_id = Column(String(255), nullable=True)
    recipient_name = Column(String(255), nullable=True)
    sender_name = Column(String(255), nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    sent_at = Column(DateTime(timezone=True), nullable=True)


class OTPRecord(Base):
    """Model to store OTP codes for password reset"""
    __tablename__ = "otp_records"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False)
    otp_code = Column(String(10), nullable=False)
    is_used = Column(Boolean, default=False)
    is_expired = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
