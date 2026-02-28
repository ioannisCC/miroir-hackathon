"""
backend/routers/decisions.py

Decision engine endpoints.
POST /decisions/evaluate/{contact_id} — run two-pass evaluation, log decision.
POST /decisions/{decision_id}/override — operator overrides with reason.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.core.database import get_db
from backend.core.logging import get_logger
from backend.services.evaluation import EvaluationPipeline

logger = get_logger(__name__)
router = APIRouter()


class OverrideRequest(BaseModel):
    action: str
    reason: str


@router.post("/evaluate/{contact_id}")
def evaluate_contact(contact_id: UUID):
    """
    Run two-pass evaluation for a contact.
    Returns next recommended action with full reasoning.
    Logs decision to decisions table.
    """
    db = get_db()

    # Load contact
    try:
        contact_result = (
            db.table("contacts")
            .select("*")
            .eq("id", str(contact_id))
            .single()
            .execute()
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Contact not found: {e}")

    contact = contact_result.data

    # Load interaction history
    try:
        history_result = (
            db.table("interactions")
            .select("*")
            .eq("contact_id", str(contact_id))
            .order("timestamp", desc=False)
            .execute()
        )
        history = history_result.data or []
    except Exception as e:
        logger.warning("Could not load history for %s: %s", contact_id, e)
        history = []

    # Run evaluation
    try:
        pipeline = EvaluationPipeline()
        result = pipeline.evaluate(contact, history)
    except Exception as e:
        logger.error("Evaluation failed for %s: %s", contact_id, e)
        raise HTTPException(status_code=500, detail=str(e))

    # Log decision to Supabase
    try:
        decision_row = {
            "contact_id": str(contact_id),
            "approach_chosen": result["action"],
            "reasoning": result["reasoning"],
            "confidence_score": result["confidence"],
            "confidence_notes": result["confidence_notes"],
            "escalate": result["escalate"],
            "outcome": None,
            "outcome_notes": "",
        }
        db.table("decisions").insert(decision_row).execute()
        logger.info(
            "Decision logged for %s — action: %s confidence: %.2f",
            contact.get("email"),
            result["action"],
            result["confidence"],
        )
    except Exception as e:
        logger.error("Failed to log decision for %s: %s", contact_id, e)
        # Don't fail the request — return result even if logging fails

    return result


@router.post("/{decision_id}/override")
def override_decision(decision_id: UUID, body: OverrideRequest):
    """
    Operator overrides a decision with a reason.
    Override reason is preserved in audit log.
    """
    db = get_db()

    try:
        result = (
            db.table("decisions")
            .update({
                "approach_chosen": body.action,
                "outcome_notes": f"OPERATOR OVERRIDE: {body.reason}",
            })
            .eq("id", str(decision_id))
            .execute()
        )
        logger.info(
            "Decision %s overridden — new action: %s reason: %s",
            decision_id,
            body.action,
            body.reason,
        )
        return {"status": "overridden", "decision_id": str(decision_id)}
    except Exception as e:
        logger.error("Override failed for %s: %s", decision_id, e)
        raise HTTPException(status_code=500, detail=str(e))