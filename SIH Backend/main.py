from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import CORS_ORIGINS, API_PREFIX
from app.core.db import init_pool, close_pool
from app.api.v1 import health, counselors, moods, journal, posts

# Create FastAPI app
app = FastAPI(
    title="Student Support API",
    description="Backend for student wellbeing platform (moods, journal, community, counselors)",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS or ["*"],  # tighten this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix=API_PREFIX, tags=["health"])
app.include_router(counselors.router, prefix=API_PREFIX, tags=["counselors"])
app.include_router(moods.router, prefix=API_PREFIX, tags=["moods"])
app.include_router(journal.router, prefix=API_PREFIX, tags=["journal"])
app.include_router(posts.router, prefix=API_PREFIX, tags=["posts"])

# Startup/shutdown events
@app.on_event("startup")
async def startup_event():
    await init_pool()

@app.on_event("shutdown")
async def shutdown_event():
    await close_pool()
