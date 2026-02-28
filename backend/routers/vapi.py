"""
backend/routers/vapi.py

Vapi integration endpoints.

POST /vapi/chat          — custom LLM endpoint. Vapi sends messages, Claude responds.
                           Profile injected fresh every turn from Supabase.

POST /vapi/webhook       — receives Vapi call lifecycle events.
                           On call-end: saves transcript to interactions table.

POST /vapi/call/{id}     — initiates outbound call to contact via Vapi API.
                           Injects contact profile as system prompt override.
"""

import json
from uuid import UUID

import anthropic
import httpx
from fastapi import APIRouter, HTTPException, Request

from backend.core.config import get_settings
from backend.core.database import get_db
from backend.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

VOICE_MAX_TOKENS = 150
VAPI_ASSISTANT_ID = "602f278d-3482-4106-80a5-3ddcf18fba9f"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _decide_tone(profile: dict) -> str:
    """Pick opening tone from profile scores."""
    follow_through = profile.get("follow_through_score") or 0.5
    pressure = profile.get("pressure_score") or 0.5

    if follow_through >= 0.7 and pressure >= 0.6:
        return "warm and collaborative"
    elif follow_through < 0.4:
        return "firm and deadline-focused"
    elif pressure < 0.4:
        return "calm and non-confrontational"
    else:
        return "professional and direct"


def _build_system_prompt(contact: dict) -> str:
    profile = contact.get("behavior_profile", {})
    risk_signals = [
        r.get("signal") if isinstance(r, dict) else str(r)
        for r in profile.get("risk_indicators", [])
    ]
    tone = _decide_tone(profile)
    debt = profile.get("debt_amount", 0)

    return f"""
You are Miroir, a professional collections specialist.

CONTACT: {contact.get('name')} <{contact.get('email')}>
OUTSTANDING DEBT: €{debt:,.0f}

BEHAVIORAL PROFILE:
{profile.get('summary', 'No profile summary available.')}

Communication tone: {profile.get('communication_tone', 'Unknown')}
Follow-through score: {profile.get('follow_through_score')} (1.0 = always follows through)
Pressure response: {profile.get('pressure_response', 'Unknown')}
Risk indicators: {json.dumps(risk_signals)}

APPROACH: Use {tone} tone. Adapt every response to what you know about this person.

HARD RULES:
- Never threaten legal action
- Never be aggressive or demeaning
- Keep responses under 3 sentences — this is a voice call
- Drive toward one specific outcome: a payment commitment with a date
- If contact is cooperative, offer a payment plan immediately
- If contact stalls, introduce a specific deadline calmly

You know this person. Speak accordingly.
""".strip()


def _load_contact(contact_id: str) -> dict:
    """Load contact from Supabase. Raises HTTPException if not found."""
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
# POST /vapi/chat — custom LLM endpoint
# ---------------------------------------------------------------------------

@router.post("/chat")
async def vapi_chat(request: Request):
    """
    Vapi custom LLM endpoint.
    Receives conversation turns, injects contact profile, returns Claude response.
    """
    try:
        body = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid request body: {e}")

    messages = body.get("messages", [])

    # Extract contact_id from multiple possible locations Vapi may send it
    contact_id = (
        body.get("contact_id")
        or body.get("metadata", {}).get("contact_id")
        or body.get("call", {}).get("metadata", {}).get("contact_id")
    )

    if not contact_id:
        logger.error("vapi/chat called without contact_id. Body keys: %s", list(body.keys()))
        raise HTTPException(status_code=400, detail="contact_id required in request or metadata")

    contact = _load_contact(str(contact_id))
    system_prompt = _build_system_prompt(contact)

    settings = get_settings()
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    try:
        response = client.messages.create(
            model=settings.claude_model,
            max_tokens=VOICE_MAX_TOKENS,
            temperature=0.3,
            system=system_prompt,
            messages=messages,
        )
    except anthropic.APIError as e:
        logger.error("Claude API error in vapi/chat: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

    text_response = response.content[0].text

    logger.info(
        "Vapi chat — contact: %s input: %d output: %d tokens",
        contact.get("email"),
        response.usage.input_tokens,
        response.usage.output_tokens,
    )

    return {
        "id": f"miroir-{response.id}",
        "object": "chat.completion",
        "choices": [{
            "message": {
                "role": "assistant",
                "content": text_response,
            }
        }],
        "metadata": {
            "contact_id": str(contact_id),
            "profile_summary": contact.get("behavior_profile", {}).get("summary", ""),
            "tone": _decide_tone(contact.get("behavior_profile", {})),
        }
    }


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

            # Dead letter queue
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
    Initiate outbound call to contact via Vapi.
    Injects behavioral profile as system prompt override.
    Contact ID passed in call metadata so webhook can link transcript.
    """
    contact = _load_contact(str(contact_id))
    settings = get_settings()

    first_name = contact.get("name", "").split()[0]
    system_prompt = _build_system_prompt(contact)

    payload = {
        "assistantId": VAPI_ASSISTANT_ID,
        "customer": {
            "number": contact.get("phone", "+30XXXXXXXXXX"),
        },
        "metadata": {
            "contact_id": str(contact_id),
        },
        "assistantOverrides": {
            "model": {
                "provider": "custom-llm",
                "url": f"{settings.backend_url}/vapi/chat",
                "model": "miroir",
                "temperature": 0.3,
                "maxTokens": VOICE_MAX_TOKENS,
                "messages": [{
                    "role": "system",
                    "content": system_prompt,
                }],
            },
            "firstMessage": (
                f"Good morning {first_name}. "
                f"I'm calling regarding an outstanding balance. "
                f"Is this a good time to talk?"
            ),
        }
    }

    async with httpx.AsyncClient(timeout=10.0) as http:
        r = await http.post(
            "https://api.vapi.ai/call",
            headers={
                "Authorization": f"Bearer {settings.vapi_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )

    if r.status_code != 201:
        logger.error("Vapi call initiation failed: %s", r.text)
        raise HTTPException(status_code=500, detail=f"Vapi error: {r.text}")

    call_data = r.json()
    logger.info(
        "Call initiated — vapi_call_id: %s contact: %s",
        call_data.get("id"),
        contact.get("email"),
    )

    return {
        "status": "calling",
        "vapi_call_id": call_data.get("id"),
        "contact_id": str(contact_id),
        "contact_name": contact.get("name"),
    }