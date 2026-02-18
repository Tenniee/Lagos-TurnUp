from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.api import routes_user
from app.api import email_routes
from app.api.routes_events import router as event_router
from app.api.rag_routes import router as ai_router
from app.core.database import Base, engine

from sqlalchemy.orm import Session
from sqlalchemy import text

from fastapi.staticfiles import StaticFiles
from app.deps.deps import get_db

from app.api.google_auth import router as google_auth_router

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from app.core.tasks import unfeature_expired_events, delete_old_events


from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
import redis.asyncio as redis

app = FastAPI(title="LagosTurnUp")
scheduler = BackgroundScheduler()


@app.on_event("startup")
def start_scheduler():
    scheduler.add_job(unfeature_expired_events, CronTrigger(hour=0, minute=0))
    scheduler.add_job(delete_old_events, CronTrigger(hour=0, minute=0))
    scheduler.start()

@app.on_event("shutdown")
def stop_scheduler():
    scheduler.shutdown()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

@app.on_event("startup")
async def startup():
    redis_client = redis.from_url("redis://localhost:6379", encoding="utf8", decode_responses=True)
    FastAPICache.init(RedisBackend(redis_client), prefix="fastapi-cache")

# Create all tables on startup
Base.metadata.create_all(bind=engine)

# Register routes
app.include_router(routes_user.router)

app.include_router(event_router, prefix="/event")
app.include_router(google_auth_router)
app.include_router(email_routes.router)
app.include_router(ai_router)



@app.get("/debug-tables")
async def debug_tables(db: Session = Depends(get_db)):
    try:
        result = db.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))
        tables = [row[0] for row in result.fetchall()]
        return {"tables": tables}
    except Exception as e:
        return {"error": str(e)}