"""
backend/services/actions.py

Actions pool and hard rules for the evaluation pipeline.
Claude selects from STANDARD_ACTIONS. HARD_RULES are evaluated before
any action is executed — violations are blocked regardless of Claude's decision.
"""

from enum import Enum


class Action(str, Enum):
    send_email = "send_email"
    send_sms = "send_sms"
    escalate_to_call = "escalate_to_call"
    escalate_to_human = "escalate_to_human"
    schedule_followup = "schedule_followup"
    close_resolved = "close_resolved"
    close_refused = "close_refused"


# Minimum confidence required before each action executes
CONFIDENCE_FLOORS = {
    Action.send_email: 0.5,
    Action.send_sms: 0.5,
    Action.escalate_to_call: 0.7,
    Action.escalate_to_human: 0.0,   # always allowed
    Action.schedule_followup: 0.5,
    Action.close_resolved: 0.9,
    Action.close_refused: 0.8,
}

# Hard rules — never overridable by Claude
# Format: (rule_id, description, check_fn signature described in comments)
HARD_RULES = [
    {
        "id": "never_call_before_two_emails",
        "description": "Cannot escalate to call until at least 2 emails have been sent",
    },
    {
        "id": "never_threaten_legal_action_without_approval",
        "description": "Legal threats require human approval before sending",
    },
    {
        "id": "never_contact_outside_business_hours",
        "description": "No outbound contact before 09:00 or after 18:00 local time",
    },
    {
        "id": "always_escalate_to_human_if_low_confidence",
        "description": "If confidence score is below 0.4, always escalate to human",
    },
    {
        "id": "always_call_on_final_deadline_day",
        "description": "On the final day of a payment deadline, escalate to call regardless of email count",
    },
]


def check_hard_rules(
    action: Action,
    contact: dict,
    interaction_history: list[dict],
    confidence: float,
) -> tuple[bool, str | None]:
    """
    Evaluate hard rules against the proposed action.
    Returns (allowed, reason_if_blocked).
    """
    # Auto-escalate to human if confidence too low
    if confidence < 0.4 and action != Action.escalate_to_human:
        return False, "Confidence below 0.4 — must escalate to human"

    # Cannot call before two emails sent
    if action == Action.escalate_to_call:
        emails_sent = sum(
            1 for i in interaction_history
            if i.get("type") == "email"
        )
        if emails_sent < 2:
            return False, f"Only {emails_sent} email(s) sent — need 2 before calling"

    # Business hours check for outbound contact actions
    outbound_actions = {Action.send_email, Action.send_sms, Action.escalate_to_call}
    if action in outbound_actions:
        try:
            from zoneinfo import ZoneInfo
            from datetime import datetime as _dt
            profile = contact.get("behavior_profile", {})
            tz_name = profile.get("timezone") or "UTC"
            local_hour = _dt.now(ZoneInfo(tz_name)).hour
            if local_hour < 9 or local_hour >= 18:
                return False, (
                    f"Outside business hours — local time is {local_hour}:00 in {tz_name}. "
                    f"No outbound contact before 09:00 or after 18:00."
                )
        except Exception:
            pass  # If timezone check fails, allow action to proceed

    # Confidence floor per action
    floor = CONFIDENCE_FLOORS.get(action, 0.5)
    if confidence < floor:
        return False, (
            f"Confidence {confidence:.2f} below floor {floor:.2f} for {action.value}"
        )

    return True, None