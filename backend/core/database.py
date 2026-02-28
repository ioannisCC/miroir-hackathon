"""
backend/core/database.py

Supabase client. Import `get_db` everywhere — never instantiate directly.
"""

from functools import lru_cache

from supabase import Client, create_client

from backend.core.config import get_settings
from backend.core.logging import get_logger

logger = get_logger(__name__)


@lru_cache
def get_db() -> Client:
    settings = get_settings()
    if not settings.supabase_configured:
        raise RuntimeError("Supabase not configured — check SUPABASE_URL and SUPABASE_SERVICE_KEY in .env")
    client = create_client(settings.supabase_url, settings.supabase_service_key)
    logger.info("Supabase client initialized")
    return client