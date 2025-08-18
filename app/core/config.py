import os
from dotenv import load_dotenv
from pathlib import Path


load_dotenv()


class Settings:
    # Your existing settings
    PROJECT_NAME = "LagosTurnUp"
    DATABASE_URL = os.getenv("DATABASE_URL")
    
    # Add these email settings to your existing class
    # Resend Configuration
    RESEND_API_KEY = os.getenv("RESEND_API_KEY")
    FROM_EMAIL = os.getenv("FROM_EMAIL", "noreply@lagosturnup.com")
    
    # Email Configuration
    OTP_EXPIRY_MINUTES = int(os.getenv("OTP_EXPIRY_MINUTES", "5"))
    OTP_LENGTH = int(os.getenv("OTP_LENGTH", "6"))
    
    # Template Configuration
    TEMPLATE_DIR = Path(__file__).parent.parent / "email_templates"
    
    # Company Information
    COMPANY_NAME = os.getenv("COMPANY_NAME", "LagosTurnUp")
    SUPPORT_EMAIL = os.getenv("SUPPORT_EMAIL", "support@lagosturnup.com")

settings = Settings()


