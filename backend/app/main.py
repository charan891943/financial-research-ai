import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.db.database import Base, engine
from app.api import sessions, documents, metrics, research, seed, milestone

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# Ensure all database tables exist
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Financial Research AI - Milestone 3",
    description="Source-grounded multi-agent financial research workspace.",
    version="3.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(sessions.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(metrics.router, prefix="/api")
app.include_router(research.router, prefix="/api")
app.include_router(seed.router, prefix="/api")
app.include_router(milestone.router, prefix="/api")

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "gemini_model": settings.GEMINI_MODEL,
        "mock_mode": settings.MOCK_AI,
        "api_key_configured": bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY != "your_gemini_api_key_here")
    }

