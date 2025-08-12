import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME = "LagosTurnUp"
    DATABASE_URL = os.getenv("DATABASE_URL")

settings = Settings()
