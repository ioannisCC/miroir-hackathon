"""
backend/services/guidelines.py

Single source of truth for company guidelines.
Fetches from Supabase. Every prompt reads from here — nothing hardcoded.
Supports presets: switch entire guideline sets with one call.
"""

from backend.core.database import get_db
from backend.core.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Preset definitions — complete guideline sets per use case
# ---------------------------------------------------------------------------

_PRESET_DEBT_COLLECTION = {
    "preset_name": "debt_collection",
    "agent_name": "Miroir",
    "agent_role": "professional collections specialist",
    "context_label": "OUTSTANDING DEBT",
    "context_value_prefix": "€",
    "first_message_template": (
        "Good morning {first_name}. "
        "I'm calling regarding an outstanding balance. "
        "Is this a good time to talk?"
    ),
    "call_rules": (
        "Never threaten legal action.\n"
        "Never be aggressive or demeaning.\n"
        "Keep responses under 3 sentences — this is a voice call.\n"
        "Drive toward one specific outcome: a payment commitment with a date.\n"
        "If the contact indicates financial hardship, proactively offer installment payment plans.\n"
        "If contact stalls, introduce a specific deadline calmly.\n"
        'Always say amounts as natural spoken words — say "five thousand euros" not "5,000".\n'
        "If contact is cooperative, reward with flexibility — offer extended timelines."
    ),
    "email_rules": (
        "Adapt tone entirely to the contact's behavioral profile.\n"
        "Never threaten legal action.\n"
        "Never use aggressive or demeaning language.\n"
        "Never create false urgency or fabricate deadlines.\n"
        "Never imply consequences you cannot deliver.\n"
        "Be specific — reference the debt amount and any prior contact.\n"
        "Keep it under 200 words.\n"
        "End with a clear single call to action.\n"
        "Sign as [Agent Name] — never impersonate a specific person.\n"
        "If prior interactions suggest financial hardship, mention installment options in the email."
    ),
    "evaluation_rules": (
        "Always escalate to human if confidence is below 0.4.\n"
        "Cannot escalate to call until at least 2 emails have been sent.\n"
        "No outbound contact before 09:00 or after 18:00 contact local time.\n"
        "On the final day of a payment deadline, escalate to call regardless of email count.\n"
        "Legal threats require human approval before sending.\n"
        "If debtor shows signs of financial hardship, recommend offering installment plans before escalating."
    ),
    "hard_rules": [
        {"id": "never_call_before_two_emails", "description": "Cannot escalate to call until at least 2 emails have been sent", "enabled": True},
        {"id": "never_threaten_legal_action_without_approval", "description": "Legal threats require human approval before sending", "enabled": True},
        {"id": "never_contact_outside_business_hours", "description": "No outbound contact before 09:00 or after 18:00 local time", "enabled": True},
        {"id": "always_escalate_to_human_if_low_confidence", "description": "If confidence score is below 0.4, always escalate to human", "enabled": True},
        {"id": "always_call_on_final_deadline_day", "description": "On the final day of a payment deadline, escalate to call regardless of email count", "enabled": True},
        {"id": "offer_installments_on_hardship", "description": "If debtor indicates financial hardship, offer installment payment plans before further escalation", "enabled": True},
    ],
    "general_context": (
        "We are Miroir, a professional debt collection service. "
        "We use behavioral intelligence to adapt our approach to each debtor. "
        "Our goal is resolution, not confrontation. "
        "We prefer payment plans over escalation. "
        "We treat every contact with dignity and respect."
    ),
}

_PRESET_RECRUITMENT = {
    "preset_name": "recruitment",
    "agent_name": "Miroir",
    "agent_role": "talent acquisition specialist",
    "context_label": "POSITION",
    "context_value_prefix": "",
    "first_message_template": (
        "Good morning {first_name}. "
        "I'm calling from Miroir Talent — we came across your profile and we're very interested. "
        "Do you have a moment to chat?"
    ),
    "call_rules": (
        "Your opening line MUST be personalized based on the candidate's behavioral profile. "
        "Reference something specific from their background — never use a generic opener.\n"
        "Example: 'We noticed your experience in distributed systems — that's exactly the profile we're looking for.'\n"
        "Be warm and enthusiastic — you are selling an opportunity, not making demands.\n"
        "Keep responses under 3 sentences — this is a voice call.\n"
        "Drive toward one specific outcome: scheduling an interview or office visit.\n"
        "If the candidate seems hesitant, highlight specific benefits (remote work, team culture, growth).\n"
        "If the candidate mentions they are already interviewing elsewhere, create urgency with timeline.\n"
        "Never pressure — always respect their decision.\n"
        "Ask one thoughtful question about their background to show genuine interest.\n"
        "If they mention salary expectations, acknowledge and say the team will follow up with details."
    ),
    "email_rules": (
        "Adapt tone entirely to the candidate's behavioral profile.\n"
        "Be warm and personalized — reference specific skills or experience from their profile.\n"
        "Never use generic recruiter language ('exciting opportunity', 'perfect fit').\n"
        "Be specific — mention the role, team, and why their background stands out.\n"
        "Keep it under 150 words — recruiters who write novels get ignored.\n"
        "End with a clear single call to action (schedule a call, visit office).\n"
        "Sign as [Agent Name] from Miroir Talent.\n"
        "If candidate has been unresponsive, try a different angle (mention a specific project or team)."
    ),
    "evaluation_rules": (
        "Always escalate to human if confidence is below 0.4.\n"
        "Cannot escalate to call until at least 1 email has been sent.\n"
        "No outbound contact before 09:00 or after 18:00 contact local time.\n"
        "If candidate indicates they accepted another offer, close as resolved — do not pursue.\n"
        "If candidate shows high interest, prioritize scheduling over more emails."
    ),
    "hard_rules": [
        {"id": "never_call_before_one_email", "description": "Cannot escalate to call until at least 1 email has been sent", "enabled": True},
        {"id": "never_contact_outside_business_hours", "description": "No outbound contact before 09:00 or after 18:00 local time", "enabled": True},
        {"id": "always_escalate_to_human_if_low_confidence", "description": "If confidence score is below 0.4, always escalate to human", "enabled": True},
        {"id": "respect_candidate_decline", "description": "If candidate explicitly declines, close as resolved — do not pursue further", "enabled": True},
        {"id": "never_discuss_salary_specifics", "description": "Never quote specific salary numbers — say the team will follow up with a detailed offer", "enabled": True},
    ],
    "general_context": (
        "We are Miroir Talent, a behavioral intelligence-powered recruitment service. "
        "We use behavioral profiling to personalize our outreach to each candidate. "
        "Our goal is to match the right people with the right roles. "
        "We treat every candidate with respect and genuine interest. "
        "We never spam — every touchpoint is intentional and personalized."
    ),
}

PRESETS = {
    "debt_collection": _PRESET_DEBT_COLLECTION,
    "recruitment": _PRESET_RECRUITMENT,
}

# Fallback defaults (debt collection)
_DEFAULTS = _PRESET_DEBT_COLLECTION


def get_guidelines() -> dict:
    """
    Fetch company guidelines from Supabase.
    Returns a dict with all guideline fields including preset metadata.
    Falls back to hardcoded defaults if DB is unreachable.
    """
    try:
        db = get_db()
        result = (
            db.table("company_guidelines")
            .select("*")
            .limit(1)
            .execute()
        )
        if result.data:
            row = result.data[0]
            return {
                "id": row.get("id"),
                "preset_name": row.get("preset_name") or _DEFAULTS["preset_name"],
                "agent_name": row.get("agent_name") or _DEFAULTS["agent_name"],
                "agent_role": row.get("agent_role") or _DEFAULTS["agent_role"],
                "context_label": row.get("context_label") or _DEFAULTS["context_label"],
                "context_value_prefix": row.get("context_value_prefix") if row.get("context_value_prefix") is not None else _DEFAULTS["context_value_prefix"],
                "first_message_template": row.get("first_message_template") or _DEFAULTS["first_message_template"],
                "call_rules": row.get("call_rules") or _DEFAULTS["call_rules"],
                "email_rules": row.get("email_rules") or _DEFAULTS["email_rules"],
                "evaluation_rules": row.get("evaluation_rules") or _DEFAULTS["evaluation_rules"],
                "hard_rules": row.get("hard_rules") or _DEFAULTS["hard_rules"],
                "general_context": row.get("general_context") or _DEFAULTS["general_context"],
                "updated_at": row.get("updated_at"),
            }
    except Exception as e:
        logger.warning("Failed to fetch guidelines from Supabase, using defaults: %s", e)

    return {**_DEFAULTS, "id": None, "updated_at": None}


def update_guidelines(updates: dict) -> dict:
    """
    Update company guidelines in Supabase.
    Accepts partial updates — only provided fields are changed.
    Returns the updated row.
    """
    db = get_db()

    current = get_guidelines()
    row_id = current.get("id")

    allowed_fields = {
        "preset_name", "agent_name", "agent_role", "context_label",
        "context_value_prefix", "first_message_template",
        "call_rules", "email_rules", "evaluation_rules", "hard_rules", "general_context",
    }
    patch = {k: v for k, v in updates.items() if k in allowed_fields}

    if not patch:
        return current

    patch["updated_at"] = "now()"

    if row_id:
        result = db.table("company_guidelines").update(patch).eq("id", row_id).execute()
    else:
        result = db.table("company_guidelines").insert(patch).execute()

    if result.data:
        return result.data[0]
    return get_guidelines()


def activate_preset(name: str) -> dict:
    """
    Activate a preset by name. Overwrites all guideline fields.
    Returns the updated guidelines.
    """
    if name not in PRESETS:
        raise ValueError(f"Unknown preset: {name}. Available: {list(PRESETS.keys())}")

    preset = PRESETS[name]
    logger.info("Activating preset: %s", name)
    return update_guidelines(preset)
