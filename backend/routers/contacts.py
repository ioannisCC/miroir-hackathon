"""
backend/routers/contacts.py

Contact management endpoints.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.core.database import get_db
from backend.core.logging import get_logger
from backend.services.email_service import EmailService

logger = get_logger(__name__)
router = APIRouter()


@router.get("")
def list_contacts():
    """Return all contacts ordered by risk score descending."""
    try:
        db = get_db()
        result = (
            db.table("contacts")
            .select("*")
            .order("risk_score", desc=True)
            .execute()
        )
        return result.data
    except Exception as e:
        logger.error("Failed to list contacts: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{contact_id}")
def get_contact(contact_id: UUID):
    """Return a single contact by ID with full profile."""
    try:
        db = get_db()
        result = (
            db.table("contacts")
            .select("*")
            .eq("id", str(contact_id))
            .single()
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Contact not found")
        return result.data
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get contact %s: %s", contact_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{contact_id}/interactions")
def get_contact_interactions(contact_id: UUID):
    """Return all interactions for a contact ordered by timestamp descending."""
    try:
        db = get_db()
        result = (
            db.table("interactions")
            .select("*")
            .eq("contact_id", str(contact_id))
            .order("timestamp", desc=True)
            .execute()
        )
        return result.data
    except Exception as e:
        logger.error("Failed to get interactions for %s: %s", contact_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{contact_id}/decisions")
def get_contact_decisions(contact_id: UUID):
    """Return all decisions for a contact ordered by created_at descending."""
    try:
        db = get_db()
        result = (
            db.table("decisions")
            .select("*")
            .eq("contact_id", str(contact_id))
            .order("created_at", desc=True)
            .execute()
        )
        return result.data
    except Exception as e:
        logger.error("Failed to get decisions for %s: %s", contact_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{contact_id}/draft-email")
def draft_email(contact_id: UUID):
    """Draft a behavioral-profile-adapted email. Does not send — returns draft."""
    db = get_db()

    try:
        contact = (
            db.table("contacts")
            .select("*")
            .eq("id", str(contact_id))
            .single()
            .execute()
            .data
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Contact not found: {e}")

    history = (
        db.table("interactions")
        .select("*")
        .eq("contact_id", str(contact_id))
        .order("timestamp")
        .execute()
        .data or []
    )

    try:
        service = EmailService()
        draft = service.draft_email(contact, history)
        return draft
    except Exception as e:
        logger.error("Email draft failed for %s: %s", contact_id, e)
        raise HTTPException(status_code=500, detail=str(e))


class ExecuteActionRequest(BaseModel):
    action: str
    decision_id: str | None = None
    override_reason: str | None = None


@router.post("/{contact_id}/execute-action")
def execute_action(contact_id: UUID, body: ExecuteActionRequest):
    """
    Operator approves an action. Logs to interactions table.
    For send_email: drafts and logs the email content.
    For escalate_to_call: logs intent, Vapi handles the rest.
    For escalate_to_human: logs and flags for human review.
    """
    db = get_db()

    try:
        contact = (
            db.table("contacts")
            .select("*")
            .eq("id", str(contact_id))
            .single()
            .execute()
            .data
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Contact not found: {e}")

    history = (
        db.table("interactions")
        .select("*")
        .eq("contact_id", str(contact_id))
        .order("timestamp")
        .execute()
        .data or []
    )

    summary = f"Action executed: {body.action}"
    transcript = ""

    # Draft and SEND email if action is send_email
    if body.action == "send_email":
        try:
            from backend.services.email_sender import send_email as _send
            from backend.core.config import get_settings

            service = EmailService()
            draft = service.draft_email(contact, history)
            transcript = f"Subject: {draft.get('subject')}\n\n{draft.get('body')}"
            summary = f"Email sent ({draft.get('tone')} tone) — {draft.get('tone_notes')}"

            settings = get_settings()
            recipient = contact.get("email") or settings.demo_email
            _send(
                to=recipient,
                subject=draft.get("subject"),
                body=draft.get("body"),
                contact_name=contact.get("name"),
            )
            logger.info("Email sent to %s", recipient)

        except Exception as e:
            logger.error("Email send failed: %s", e)
            raise HTTPException(status_code=500, detail=str(e))

    # Log interaction
    try:
        interaction_type = (
            "email" if body.action == "send_email"
            else "call" if "call" in body.action
            else "email"
        )
        interaction = {
            "contact_id": str(contact_id),
            "type": interaction_type,
            "transcript": transcript,
            "summary": summary,
        }
        result = db.table("interactions").insert(interaction).execute()
        interaction_id = result.data[0]["id"] if result.data else None
        logger.info("Action %s logged for %s", body.action, contact.get("email"))
    except Exception as e:
        logger.error("Failed to log interaction: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

    # Update decision outcome if decision_id provided
    if body.decision_id:
        try:
            db.table("decisions").update({
                "outcome": "other",
                "outcome_notes": (
                    f"Action executed: {body.action}"
                    + (f" | Override: {body.override_reason}" if body.override_reason else "")
                ),
            }).eq("id", body.decision_id).execute()
        except Exception as e:
            logger.warning("Failed to update decision outcome: %s", e)

    return {
        "status": "executed",
        "action": body.action,
        "contact_id": str(contact_id),
        "interaction_id": interaction_id,
        "summary": summary,
        "transcript": transcript,
    }

class PostCallRequest(BaseModel):
    transcript: str
    interaction_id: str | None = None


@router.post("/{contact_id}/post-call")
def post_call_analysis(contact_id: UUID, body: PostCallRequest):
    """
    Run post-call analysis on a transcript.
    Updates behavioral profile in Supabase.
    Returns before/after delta for dashboard display.
    """
    from backend.services.post_call import PostCallAnalyzer

    db = get_db()

    try:
        contact = (
            db.table("contacts")
            .select("*")
            .eq("id", str(contact_id))
            .single()
            .execute()
            .data
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Contact not found: {e}")

    try:
        analyzer = PostCallAnalyzer()
        analysis = analyzer.analyze(contact, body.transcript)
        result = analyzer.apply_delta(contact, analysis)
    except Exception as e:
        logger.error("Post-call analysis failed for %s: %s", contact_id, e)
        raise HTTPException(status_code=500, detail=str(e))

    # Write updated profile to Supabase
    try:
        db.table("contacts").update({
            "behavior_profile": result["updated_profile"],
            "trust_score": result["trust_score"],
            "risk_score": result["risk_score"],
        }).eq("id", str(contact_id)).execute()

        # Update interaction summary if interaction_id provided
        if body.interaction_id:
            db.table("interactions").update({
                "summary": analysis.get("outcome_notes", "Call analyzed"),
            }).eq("id", body.interaction_id).execute()

        logger.info(
            "Profile updated post-call — contact: %s outcome: %s changed: %s",
            contact.get("email"),
            analysis.get("outcome"),
            result["delta"]["changed_fields"],
        )
    except Exception as e:
        logger.error("Failed to write post-call update: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "outcome": analysis.get("outcome"),
        "outcome_notes": analysis.get("outcome_notes"),
        "new_signals": analysis.get("new_signals", []),
        "score_reasoning": analysis.get("score_reasoning", {}),
        "delta": result["delta"],
        "contact_id": str(contact_id),
    }