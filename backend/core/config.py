"""
backend/core/config.py

Central configuration. All environment variables loaded here.
Every other module imports `settings` from this file — never reads env directly.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/.env — resolved relative to this file, works regardless of cwd
ENV_FILE = Path(__file__).parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # --- Anthropic ---
    anthropic_api_key: str
    claude_model: str = "claude-sonnet-4-20250514"

    # --- Supabase ---
    supabase_url: str = ""
    supabase_service_key: str = ""

    # --- Vapi ---
    vapi_api_key: str = ""
    vapi_phone_number_id: str = "d2380b9a-3dfb-4248-a47f-62e227759e54"
    elevenlabs_voice_id: str = "21m00Tcm4TlvDq8ikWAM"
    backend_url: str = "http://localhost:8000"  # for Vapi callbacks

    # --- App ---
    environment: str = "development"
    log_level: str = "INFO"

    # --- Profile extraction ---
    min_threads_for_profile: int = 10
    max_threads_per_contact: int = 10

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def supabase_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_key)

    @property
    def vapi_configured(self) -> bool:
        return bool(self.vapi_api_key and self.vapi_phone_number_id)


@lru_cache
def get_settings() -> Settings:
    """
    Cached settings instance.
    Use this everywhere: from backend.core.config import get_settings
    settings = get_settings()
    """
    return Settings()