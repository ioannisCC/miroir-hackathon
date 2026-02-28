"""
backend/routers/guidelines.py

Company guidelines endpoints.
GET  /guidelines     — read current guidelines (for frontend display)
PUT  /guidelines     — update guidelines (operator edits from dashboard)
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.core.logging import get_logger
from backend.services.guidelines import get_guidelines, update_guidelines

logger = get_logger(__name__)
router = APIRouter()


class GuidelinesUpdate(BaseModel):
    call_rules: str | None = None
    email_rules: str | None = None
    evaluation_rules: str | None = None
    hard_rules: list[dict] | None = None
    general_context: str | None = None


@router.get("")
def read_guidelines():
    """Return current company guidelines."""
    try:
        return get_guidelines()
    except Exception as e:
        logger.error("Failed to read guidelines: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("")
def write_guidelines(body: GuidelinesUpdate):
    """Update company guidelines. Partial updates accepted."""
    try:
        updates = body.model_dump(exclude_none=True)
        result = update_guidelines(updates)
        logger.info("Guidelines updated — fields: %s", list(updates.keys()))
        return result
    except Exception as e:
        logger.error("Failed to update guidelines: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
