from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# Use SSL cert only if it's a hosted DB (not sqlite)
if settings.DATABASE_URL.startswith("mysql"):
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={
            "ssl": {
                "ca": "certs/lagos-cert.pem"  # path to downloaded cert
            }
        }
    )
else:
    engine = create_engine(settings.DATABASE_URL)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()
