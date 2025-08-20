from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr


# Request Schemas
class CustomEmailRequest(BaseModel):
    to_email: EmailStr
    subject: str
    recipient_name: str
    custom_message: str
    sender_name: Optional[str] = "Your App Team"


class OTPEmailRequest(BaseModel):
    to_email: EmailStr
    recipient_name: str


class OTPVerificationRequest(BaseModel):
    email: EmailStr
    otp: str


# Response Schemas
class EmailResponse(BaseModel):
    message: str
    recipient: str
    email_id: Optional[int] = None
    status: str = "sent"


class OTPResponse(BaseModel):
    message: str
    recipient: str
    expires_in_minutes: int
    email_id: Optional[int] = None


class OTPVerificationResponse(BaseModel):
    message: str
    email: str
    verified: bool = True


class EmailLogResponse(BaseModel):
    id: int
    to_email: str
    from_email: str
    subject: str
    email_type: str
    status: str
    recipient_name: Optional[str]
    sender_name: Optional[str]
    created_at: datetime
    sent_at: Optional[datetime]

    class Config:
        from_attributes = True


class OTPRecordResponse(BaseModel):
    id: int
    email: str
    is_used: bool
    is_expired: bool
    created_at: datetime
    expires_at: datetime

    class Config:
        from_attributes = True


class BroadcastEmailRequest(BaseModel):
    subject: str
    custom_message: str
    sender_name: Optional[str] = "Lagos Turn Up Team"


class BroadcastEmailResponse(BaseModel):
    message: str
    total_subscribers: int
    emails_sent: int
    failed_emails: int
    status: str
    email_logs: List[int]