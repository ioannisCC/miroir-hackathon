"""
backend/services/guidelines.py

Single source of truth for company guidelines.
Fetches from Supabase. Every prompt reads from here — nothing hardcoded.
"""

from backend.core.database import get_db
from backend.core.logging import get_logger

logger = get_logger(__name__)

# Fallback defaults if Supabase is unreachable or table is empty
_DEFAULTS = {
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


def get_guidelines() -> dict:
    """
    Fetch company guidelines from Supabase.
    Returns a dict with keys: call_rules, email_rules, evaluation_rules,
    hard_rules, general_context.
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

    allowed_fields = {"call_rules", "email_rules", "evaluation_rules", "hard_rules", "general_context"}
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
