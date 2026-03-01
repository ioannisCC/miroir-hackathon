"""
backend/routers/guidelines.py

Company guidelines endpoints.
GET  /guidelines            — read current guidelines (for frontend display)
PUT  /guidelines            — update guidelines (operator edits from dashboard)
POST /guidelines/preset/{n} — switch entire guideline preset (debt_collection / recruitment)
GET  /guidelines/active     — lightweight: returns active preset name + role + context label
GET  /guidelines/presets    — list available preset names
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.core.logging import get_logger
from backend.services.guidelines import (
    get_guidelines,
    update_guidelines,
    activate_preset,
    PRESETS,
)

logger = get_logger(__name__)
router = APIRouter()


class GuidelinesUpdate(BaseModel):
    preset_name: str | None = None
    agent_name: str | None = None
    agent_role: str | None = None
    context_label: str | None = None
    context_value_prefix: str | None = None
    first_message_template: str | None = None
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


@router.post("/preset/{name}")
def switch_preset(name: str):
    """Activate a preset by name. Overwrites all guideline fields."""
    try:
        result = activate_preset(name)
        logger.info("Preset activated: %s", name)
        return {"status": "ok", "preset": name, "guidelines": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to activate preset '%s': %s", name, e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/active")
def active_preset():
    """Lightweight endpoint: returns just the active preset metadata."""
    try:
        gl = get_guidelines()
        return {
            "preset_name": gl.get("preset_name", "debt_collection"),
            "agent_name": gl.get("agent_name", "Miroir"),
            "agent_role": gl.get("agent_role"),
            "context_label": gl.get("context_label"),
        }
    except Exception as e:
        logger.error("Failed to get active preset: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/presets")
def list_presets():
    """Return available preset names."""
    return {"presets": list(PRESETS.keys())}
