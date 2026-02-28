"""
backend/main.py

FastAPI application entry point.
Run: uv run uvicorn backend.main:app --reload --port 8000
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.core.config import get_settings
from backend.core.database import get_db
from backend.core.logging import get_logger, setup_logging
from backend.routers import contacts, decisions, contracts, vapi
from backend.services.scheduler import scheduler

setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info("Starting Miroir — environment: %s", settings.environment)

    try:
        get_db()
        logger.info("Supabase connection verified")
    except Exception as e:
        logger.error("Supabase connection failed: %s", e)
        raise

    # Autonomous scheduler — dormant until follow_ups table has rows
    scheduler.start()
    logger.info("Autonomous scheduler started — checking every 60 seconds")

    yield

    scheduler.shutdown()
    logger.info("Miroir shutting down")


app = FastAPI(
    title="Miroir",
    description="Behavioral intelligence layer — autonomous collections operator",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(contacts.router, prefix="/contacts", tags=["contacts"])
app.include_router(decisions.router, prefix="/decisions", tags=["decisions"])
app.include_router(contracts.router, prefix="/contracts", tags=["contracts"])
app.include_router(vapi.router, prefix="/vapi", tags=["vapi"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    settings = get_settings()
    return {
        "status": "ok",
        "environment": settings.environment,
        "supabase": settings.supabase_configured,
        "vapi": settings.vapi_configured,
    }