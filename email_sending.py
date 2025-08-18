import os
import resend
from typing import List
import random
import string
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

# Configure Resend
resend.api_key = os.getenv("RESEND_API_KEY")
FROM_EMAIL = os.getenv("FROM_EMAIL", "noreply@yourdomain.com")  # Use your verified domain



def generate_otp() -> str:
    """Generate 6-digit OTP"""
    return ''.join(random.choices(string.digits, k=6))

def send_otp_email(email: str, otp: str, user_name: str = None) -> bool:
    """Send OTP email for password reset"""
    try:
        # Create HTML template
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .otp {{ background: #4CAF50; color: white; font-size: 32px; font-weight: bold; padding: 15px 30px; border-radius: 8px; text-align: center; margin: 20px 0; letter-spacing: 5px; }}
                .warning {{ background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔐 Password Reset Request</h1>
                </div>
                <div class="content">
                    <p>Hello {user_name or 'there'},</p>
                    <p>We received a request to reset your password. Use the OTP code below to proceed:</p>
                    
                    <div class="otp">{otp}</div>
                    
                    <div class="warning">
                        <strong>⚠️ Important:</strong>
                        <ul>
                            <li>This OTP is valid for <strong>10 minutes</strong> only</li>
                            <li>Don't share this code with anyone</li>
                            <li>If you didn't request this, please ignore this email</li>
                        </ul>
                    </div>
                    
                    <p>Enter this code on the password reset page to create your new password.</p>
                </div>
                <div class="footer">
                    <p>This is an automated message, please don't reply to this email.</p>
                    <p>&copy; 2025 Your App Name. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Plain text version
        text_content = f"""
        Password Reset Request
        
        Hello {user_name or 'there'},
        
        We received a request to reset your password. Use this OTP code: {otp}
        
        This code is valid for 10 minutes only.
        If you didn't request this, please ignore this email.
        
        Your App Name Team
        """
        
        # Send email
        params = {{
            "from": FROM_EMAIL,
            "to": [email],
            "subject": "🔐 Your Password Reset Code",
            "html": html_content,
            "text": text_content,
        }}
        
        response = resend.Emails.send(params)
        return True
        
    except Exception as e:
        print(f"Failed to send OTP email: {{e}}")
        return False
