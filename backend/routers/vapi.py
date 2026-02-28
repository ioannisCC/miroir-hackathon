"""
backend/routers/vapi.py

Vapi integration endpoints.

POST /vapi/webhook       — receives Vapi call lifecycle events.
                           On call-end: saves transcript to interactions table.

POST /vapi/call/{id}     — initiates outbound call to contact via Vapi API.
                           Full assistant defined inline — no dashboard config needed.
                           Claude is the model. ElevenLabs is the voice.
                           Profile injected as system prompt per contact.
"""

import json
from uuid import UUID

import httpx
from fastapi import APIRouter, HTTPException, Request

from backend.core.config import get_settings
from backend.core.database import get_db
from backend.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

DEMO_PHONE = "+306986903946"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_system_prompt(contact: dict) -> str:
    profile = contact.get("behavior_profile", {})
    risk_signals = [
        r.get("signal") if isinstance(r, dict) else str(r)
        for r in profile.get("risk_indicators", [])
    ]
    debt = profile.get("debt_amount", 0)

    return f"""You are Miroir, a professional collections specialist.

CONTACT: {contact.get('name')} <{contact.get('email')}>
OUTSTANDING DEBT: €{debt:,.0f}

BEHAVIORAL PROFILE:
{profile.get('summary', 'No profile summary available.')}

Communication tone: {profile.get('communication_tone', 'Unknown')}
Follow-through score: {profile.get('follow_through_score')} (1.0 = always follows through)
Pressure response: {profile.get('pressure_response', 'Unknown')}
Risk indicators: {json.dumps(risk_signals)}

Read this profile carefully. Decide your own tone and strategy based on what you know about this person.
Adapt mid-call based on their responses.

HARD RULES:
- Never threaten legal action
- Never be aggressive or demeaning
- Keep responses under 3 sentences — this is a voice call
- Drive toward one specific outcome: a payment commitment with a date
- If contact is cooperative, offer a payment plan immediately
- If contact stalls, introduce a specific deadline calmly

You know this person. Speak accordingly."""


def _load_contact(contact_id: str) -> dict:
    try:
        db = get_db()
        contact = (
            db.table("contacts")
            .select("*")
            .eq("id", contact_id)
            .single()
            .execute()
            .data
        )
        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")
        return contact
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to load contact %s: %s", contact_id, e)
        raise HTTPException(status_code=404, detail=f"Contact not found: {e}")


# ---------------------------------------------------------------------------
# POST /vapi/webhook — call lifecycle events
# ---------------------------------------------------------------------------

@router.post("/webhook")
async def vapi_webhook(request: Request):
    """
    Vapi call lifecycle webhook.
    On end-of-call-report: saves transcript to interactions table.
    Failed writes go to failed_actions dead letter queue.
    """
    try:
        body = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid webhook body: {e}")

    event_type = (
        body.get("message", {}).get("type")
        or body.get("type", "")
    )

    contact_id = (
        body.get("message", {}).get("call", {}).get("metadata", {}).get("contact_id")
        or body.get("call", {}).get("metadata", {}).get("contact_id")
        or body.get("metadata", {}).get("contact_id")
    )

    logger.info("Vapi webhook — event: %s contact: %s", event_type, contact_id)

    if event_type in ("end-of-call-report", "call-ended"):
        if not contact_id:
            logger.warning("end-of-call-report missing contact_id")
            return {"status": "ignored", "reason": "no contact_id"}

        transcript = (
            body.get("message", {}).get("transcript")
            or body.get("transcript", "")
        )
        summary = (
            body.get("message", {}).get("summary")
            or body.get("summary", "Call completed")
        )

        db = get_db()

        try:
            result = db.table("interactions").insert({
                "contact_id": str(contact_id),
                "type": "call",
                "transcript": transcript,
                "summary": summary,
            }).execute()

            interaction_id = result.data[0]["id"] if result.data else None
            logger.info(
                "Transcript saved — contact: %s interaction: %s",
                contact_id,
                interaction_id,
            )

            return {
                "status": "saved",
                "contact_id": str(contact_id),
                "interaction_id": interaction_id,
            }

        except Exception as e:
            logger.error("Failed to save transcript for %s: %s", contact_id, e)

            try:
                db.table("failed_actions").insert({
                    "contact_id": str(contact_id),
                    "action_type": "save_call_transcript",
                    "payload": body,
                    "error_message": str(e),
                    "retry_count": 0,
                    "status": "pending",
                }).execute()
            except Exception:
                pass

            raise HTTPException(status_code=500, detail=str(e))

    return {"status": "ok", "event": event_type}


# ---------------------------------------------------------------------------
# POST /vapi/call/{contact_id} — initiate outbound call
# ---------------------------------------------------------------------------

@router.post("/call/{contact_id}")
async def start_call(contact_id: UUID):
    """
    Initiate outbound call via Vapi.
    Assistant defined fully inline — Claude as model, ElevenLabs as voice.
    No Vapi dashboard assistant needed.
    Falls back to DEMO_PHONE if contact has no phone in profile.
    """
    contact = _load_contact(str(contact_id))
    settings = get_settings()

    first_name = contact.get("name", "").split()[0]
    system_prompt = _build_system_prompt(contact)
    phone = contact.get("behavior_profile", {}).get("phone") or DEMO_PHONE

    payload = {
        "assistant": {
            "model": {
                "provider": "anthropic",
                "model": "claude-sonnet-4-20250514",
                "temperature": 0.3,
                "maxTokens": 150,
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt,
                    }
                ],
            },
            "voice": {
                "provider": "11labs",
                "voiceId": settings.elevenlabs_voice_id,
                "model": "eleven_v3",
                "stability": 0.5,
                "similarityBoost": 0.75,
            },
            "transcriber": {
                "provider": "deepgram",
                "model": "nova-3",
                "language": "en",
            },
            "firstMessage": (
                f"Good morning {first_name}. "
                f"I'm calling regarding an outstanding balance. "
                f"Is this a good time to talk?"
            ),
            "endCallPhrases": ["goodbye", "talk soon", "thank you goodbye"],
            "serverUrl": f"{settings.backend_url}/vapi/webhook",
        },
        "customer": {
            "number": phone,
        },
        "metadata": {
            "contact_id": str(contact_id),
        },
    }

    async with httpx.AsyncClient(timeout=15.0) as http:
        r = await http.post(
            "https://api.vapi.ai/call/phone",
            headers={
                "Authorization": f"Bearer {settings.vapi_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )

    if r.status_code != 201:
        logger.error("Vapi call failed: %s", r.text)
        raise HTTPException(status_code=500, detail=f"Vapi error: {r.text}")

    call_data = r.json()
    logger.info(
        "Call initiated — vapi_call_id: %s contact: %s phone: %s",
        call_data.get("id"),
        contact.get("email"),
        phone,
    )

    return {
        "status": "calling",
        "vapi_call_id": call_data.get("id"),
        "contact_id": str(contact_id),
        "contact_name": contact.get("name"),
        "phone": phone,
    }