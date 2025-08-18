from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import routes_user
from app.api import email_routes
from app.api.routes_events import router as event_router
from app.core.database import Base, engine
from fastapi.staticfiles import StaticFiles

from app.api.google_auth import router as google_auth_router

app = FastAPI(title="LagosTurnUp")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")



# Create all tables on startup
Base.metadata.create_all(bind=engine)

# Register routes
app.include_router(routes_user.router)

app.include_router(event_router, prefix="/event")
app.include_router(google_auth_router)
app.include_router(email_routes.router)

@app.get("/debug-all-routes")
async def debug_all_routes():
    routes = []
    for route in app.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            routes.append({
                "path": route.path,
                "methods": list(route.methods),
                "name": getattr(route, 'name', 'unnamed')
            })
    return {"routes": routes}