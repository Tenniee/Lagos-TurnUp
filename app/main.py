from fastapi import FastAPI
from app.api import routes_user
from app.api.routes_events import router as event_router
from app.core.database import Base, engine

app = FastAPI(title="LagosTurnUp")

# Create all tables on startup
Base.metadata.create_all(bind=engine)

# Register routes
app.include_router(routes_user.router)

app.include_router(event_router, prefix="/event")
