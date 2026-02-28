"""
backend/routers/vapi.py

Voice call endpoints.
VOICE_PROVIDER=elevenlabs → ElevenLabs outbound call
VOICE_PROVIDER=vapi       → Vapi outbound call

POST /vapi/call/{contact_id} — unified endpoint, routes based on config
POST /vapi/webhook           — handles both Vapi and ElevenLabs events
"""

import json
from datetime import datetime, timedelta, timezone
from uuid import UUID

import httpx
from fastapi import APIRouter, HTTPException, Request

from backend.core.config import get_settings
from backend.core.database import get_db
from backend.core.logging import get_logger
from backend.services.guidelines import get_guidelines

logger = get_logger(__name__)
router = APIRouter()

DEMO_PHONE = "+306986903946"


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _build_system_prompt(contact: dict) -> str:
    profile = contact.get("behavior_profile", {})
    risk_signals = [
        r.get("signal") if isinstance(r, dict) else str(r)
        for r in profile.get("risk_indicators", [])
    ]
    debt = profile.get("debt_amount", 0)

    # Fetch live guidelines from Supabase
    gl = get_guidelines()
    call_rules = gl["call_rules"]
    general_context = gl["general_context"]

    # Format call rules as bullet list
    rules_block = "\n".join(f"- {line.strip()}" for line in call_rules.split("\n") if line.strip())

    return f"""You are Miroir, a professional collections specialist.
{general_context}

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

RULES:
{rules_block}

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
# ElevenLabs outbound call
# ---------------------------------------------------------------------------

async def _start_call_elevenlabs(contact: dict, contact_id: str) -> dict:
    settings = get_settings()

    first_name = contact.get("name", "").split()[0]
    system_prompt = _build_system_prompt(contact)
    phone = contact.get("behavior_profile", {}).get("phone") or DEMO_PHONE

    payload = {
        "agent_id": settings.elevenlabs_agent_id,
        "agent_phone_number_id": settings.elevenlabs_phone_number_id,
        "to_number": phone,
        "conversation_initiation_client_data": {
            "dynamic_variables": {
                "contact_id": contact_id,
            },
            "conversation_config_override": {
                "agent": {
                    "prompt": {
                        "prompt": system_prompt,
                    },
                    "first_message": (
                        f"Good morning {first_name}. "
                        f"I'm calling regarding an outstanding balance. "
                        f"Is this a good time to talk?"
                    ),
                }
            },
        },
    }

    async with httpx.AsyncClient(timeout=15.0) as http:
        r = await http.post(
            "https://api.elevenlabs.io/v1/convai/twilio/outbound-call",
            headers={
                "xi-api-key": settings.elevenlabs_api_key,
                "Content-Type": "application/json",
            },
            json=payload,
        )

    if r.status_code not in (200, 201):
        logger.error("ElevenLabs call failed: %s", r.text)
        raise HTTPException(status_code=500, detail=f"ElevenLabs error: {r.text}")

    call_data = r.json()
    logger.info(
        "ElevenLabs call initiated — conversation_id: %s contact: %s phone: %s",
        call_data.get("conversation_id"),
        contact.get("email"),
        phone,
    )

    return {
        "status": "calling",
        "provider": "elevenlabs",
        "conversation_id": call_data.get("conversation_id"),
        "contact_id": contact_id,
        "contact_name": contact.get("name"),
        "phone": phone,
    }


# ---------------------------------------------------------------------------
# Vapi outbound call
# ---------------------------------------------------------------------------

async def _start_call_vapi(contact: dict, contact_id: str) -> dict:
    settings = get_settings()

    first_name = contact.get("name", "").split()[0]
    system_prompt = _build_system_prompt(contact)
    phone = contact.get("behavior_profile", {}).get("phone") or DEMO_PHONE

    payload = {
        "phoneNumberId": settings.vapi_phone_number_id,
        "assistant": {
            "model": {
                "provider": "anthropic",
                "model": "claude-sonnet-4-20250514",
                "temperature": 0.3,
                "maxTokens": 150,
                "messages": [{"role": "system", "content": system_prompt}],
            },
            "voice": {
                "provider": "11labs",
                "voiceId": settings.elevenlabs_voice_id,
                "model": "eleven_turbo_v2_5",
                "stability": 0.35,
                "similarityBoost": 0.85,
                "style": 0.45,
                "useSpeakerBoost": True,
                "speed": 0.95,
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
            "startSpeakingPlan": {"waitSeconds": 0.4, "smartEndpointingEnabled": True},
            "stopSpeakingPlan": {"numWords": 2, "voiceSeconds": 0.3, "backoffSeconds": 0.8},
            "silenceTimeoutSeconds": 30,
            "maxDurationSeconds": 300,
            "serverUrl": f"{settings.backend_url}/vapi/webhook",
        },
        "customer": {"number": phone},
        "metadata": {"contact_id": contact_id},
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
        "Vapi call initiated — call_id: %s contact: %s phone: %s",
        call_data.get("id"),
        contact.get("email"),
        phone,
    )

    return {
        "status": "calling",
        "provider": "vapi",
        "vapi_call_id": call_data.get("id"),
        "contact_id": contact_id,
        "contact_name": contact.get("name"),
        "phone": phone,
    }


# ---------------------------------------------------------------------------
# Unified call endpoint — routes based on VOICE_PROVIDER config
# ---------------------------------------------------------------------------

@router.post("/call/{contact_id}")
async def start_call(contact_id: UUID):
    """
    Initiate outbound call.
    Routes to ElevenLabs or Vapi based on VOICE_PROVIDER setting.
    Switch providers by changing VOICE_PROVIDER env var — no code changes.
    """
    contact = _load_contact(str(contact_id))
    settings = get_settings()

    logger.info(
        "Starting call — provider: %s contact: %s",
        settings.voice_provider,
        contact.get("email"),
    )

    if settings.voice_provider == "elevenlabs":
        return await _start_call_elevenlabs(contact, str(contact_id))
    else:
        return await _start_call_vapi(contact, str(contact_id))


# ---------------------------------------------------------------------------
# Webhook — handles both Vapi and ElevenLabs event formats
# ---------------------------------------------------------------------------

@router.post("/webhook")
async def vapi_webhook(request: Request):
    """
    Unified webhook for Vapi and ElevenLabs call lifecycle events.
    On call end:
      1. Save transcript
      2. Post-call analysis — updates profile
      3. Schedule next follow-up automatically
      4. Send human escalation briefing if refused_engagement
    """
    try:
        body = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid webhook body: {e}")

    # Normalise event type — Vapi and ElevenLabs use different field names
    event_type = (
        body.get("type")
        or body.get("message", {}).get("type")
        or ""
    )

    # Normalise contact_id — ElevenLabs nests in data.conversation_initiation_client_data
    contact_id = (
        body.get("data", {})
            .get("conversation_initiation_client_data", {})
            .get("dynamic_variables", {})
            .get("contact_id")
        or body.get("metadata", {}).get("contact_id")
        or body.get("message", {}).get("call", {}).get("metadata", {}).get("contact_id")
    )

    # Normalise transcript — ElevenLabs sends array of turns, Vapi sends string
    raw_transcript = (
        body.get("data", {}).get("transcript")
        or body.get("transcript")
        or body.get("message", {}).get("transcript")
        or []
    )
    if isinstance(raw_transcript, list):
        transcript = "\n".join(
            f"{t.get('role', 'unknown').upper()}: {t.get('message', '')}"
            for t in raw_transcript
        )
    else:
        transcript = raw_transcript or ""

    # Normalise summary
    summary = (
        body.get("analysis", {}).get("summary")
        or body.get("message", {}).get("summary")
        or body.get("summary")
        or "Call completed"
    )

    logger.info("Webhook — event: %s contact: %s", event_type, contact_id)

    END_EVENTS = {
        "end-of-call-report",        # Vapi
        "call-ended",                # Vapi
        "post_call_transcription",   # ElevenLabs
    }

    if event_type not in END_EVENTS:
        return {"status": "ok", "event": event_type}

    if not contact_id:
        logger.warning("End event missing contact_id — body: %s", str(body)[:200])
        return {"status": "ignored", "reason": "no contact_id"}

    db = get_db()

    # Step 1 — Save transcript
    interaction_id = None
    try:
        result = db.table("interactions").insert({
            "contact_id": str(contact_id),
            "type": "call",
            "transcript": transcript,
            "summary": summary,
        }).execute()
        interaction_id = result.data[0]["id"] if result.data else None
        logger.info("Transcript saved — contact: %s interaction: %s", contact_id, interaction_id)
    except Exception as e:
        logger.error("Failed to save transcript: %s", e)
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

    # Steps 2-4 — Post-call analysis (non-fatal)
    outcome = "other"
    delta = {}

    if transcript:
        try:
            from backend.services.post_call import PostCallAnalyzer

            contact = _load_contact(str(contact_id))
            analyzer = PostCallAnalyzer()
            analysis = analyzer.analyze(contact, transcript)
            result_delta = analyzer.apply_delta(contact, analysis)
            outcome = analysis.get("outcome", "other")
            delta = result_delta.get("delta", {})

            db.table("contacts").update({
                "behavior_profile": result_delta["updated_profile"],
                "trust_score": result_delta["trust_score"],
                "risk_score": result_delta["risk_score"],
            }).eq("id", str(contact_id)).execute()

            if interaction_id:
                db.table("interactions").update({
                    "summary": analysis.get("outcome_notes", summary),
                }).eq("id", interaction_id).execute()

            logger.info(
                "Profile updated — contact: %s outcome: %s changed: %s",
                contact_id, outcome, delta.get("changed_fields", []),
            )

            # Step 3 — Schedule next follow-up
            outcome_to_next = {
                "promise_to_pay":      ("evaluate",          7),
                "payment_plan_agreed": ("evaluate",         14),
                "no_answer":           ("escalate_to_call",  3),
                "callback_scheduled":  ("escalate_to_call",  2),
                "refused_engagement":  ("escalate_to_human", 0),
                "paid_now":            None,
                "other":               ("evaluate",          4),
            }

            next_config = outcome_to_next.get(outcome, ("evaluate", 4))
            if next_config is not None:
                next_action, delay_days = next_config
                scheduled_at = (
                    datetime.now(timezone.utc) + timedelta(days=delay_days)
                ).isoformat()
                db.table("follow_ups").insert({
                    "contact_id": str(contact_id),
                    "scheduled_at": scheduled_at,
                    "action_type": next_action,
                    "status": "pending",
                }).execute()
                logger.info(
                    "Follow-up scheduled — contact: %s action: %s in %d days",
                    contact_id, next_action, delay_days,
                )

            # Step 4 — Human escalation briefing email
            if outcome == "refused_engagement":
                try:
                    from backend.services.human_escalation import generate_briefing
                    from backend.services.email_sender import send_email as _send

                    history = (
                        db.table("interactions")
                        .select("*")
                        .eq("contact_id", str(contact_id))
                        .order("timestamp")
                        .execute()
                        .data or []
                    )
                    briefing = generate_briefing(contact, history)
                    _send(
                        to="ioanniscatargiu@outlook.com",
                        subject=f"🚨 Human Escalation Required — {contact.get('name')}",
                        body=briefing,
                        contact_name=contact.get("name"),
                    )
                    logger.info("Human escalation briefing sent for %s", contact.get("name"))
                except Exception as e:
                    logger.error("Failed to send escalation briefing (non-fatal): %s", e)

        except Exception as e:
            logger.error("Post-call analysis failed (non-fatal): %s", e)

    return {
        "status": "saved",
        "contact_id": str(contact_id),
        "interaction_id": interaction_id,
        "outcome": outcome,
        "delta": delta,
    }


# ---------------------------------------------------------------------------
# System prompt endpoint — for frontend ElevenLabs browser sessions
# ---------------------------------------------------------------------------

@router.get("/prompt/{contact_id}")
def get_call_prompt(contact_id: UUID):
    """
    Returns the system prompt for a contact.
    Used by frontend to inject profile into ElevenLabs browser session.
    """
    contact = _load_contact(str(contact_id))
    first_name = contact.get("name", "").split()[0]
    return {
        "system_prompt": _build_system_prompt(contact),
        "first_message": (
            f"Good morning {first_name}. "
            f"I'm calling regarding an outstanding balance. "
            f"Is this a good time to talk?"
        ),
        "contact_name": contact.get("name"),
    }